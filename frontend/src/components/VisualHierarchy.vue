<template>
  <div class="visual-hierarchy">
    <!-- 视觉层次展示区域 -->
    <div class="hierarchy-showcase">
      <div class="showcase-header">
        <h1 class="title-level-1">视觉层次设计系统</h1>
        <p class="description">展示色彩系统、8px网格、三级字体和留白设计</p>
      </div>

      <!-- 色彩系统展示 -->
      <div class="color-system-section">
        <h2 class="title-level-2">色彩系统</h2>
        <p class="text-secondary">基于财经行业色彩心理学的三色配色方案</p>
        
        <div class="color-palette">
          <!-- 主色调 -->
          <div class="color-group">
            <h3 class="title-level-3">主色调 - 信任蓝</h3>
            <div class="color-swatches">
              <div class="color-swatch primary-color-light">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">浅蓝</div>
                  <div class="swatch-hex">#E3F2FD</div>
                  <div class="swatch-usage">背景、悬停状态</div>
                </div>
              </div>
              <div class="color-swatch primary-color">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">主蓝</div>
                  <div class="swatch-hex">#2C7BE5</div>
                  <div class="swatch-usage">主按钮、链接</div>
                </div>
              </div>
              <div class="color-swatch primary-color-dark">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">深蓝</div>
                  <div class="swatch-hex">#1B4F72</div>
                  <div class="swatch-usage">标题、重要文本</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 成功色调 -->
          <div class="color-group">
            <h3 class="title-level-3">成功色调 - 增长绿</h3>
            <div class="color-swatches">
              <div class="color-swatch success-color-light">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">浅绿</div>
                  <div class="swatch-hex">#E8F5E8</div>
                  <div class="swatch-usage">成功提示背景</div>
                </div>
              </div>
              <div class="color-swatch success-color">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">增长绿</div>
                  <div class="swatch-hex">#00D97E</div>
                  <div class="swatch-usage">涨幅、成功状态</div>
                </div>
              </div>
              <div class="color-swatch success-color-dark">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">深绿</div>
                  <div class="swatch-hex">#007B4B</div>
                  <div class="swatch-usage">成功文本</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 危险色调 -->
          <div class="color-group">
            <h3 class="title-level-3">危险色调 - 负面红</h3>
            <div class="color-swatches">
              <div class="color-swatch danger-color-light">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">浅红</div>
                  <div class="swatch-hex">#FEE2E2</div>
                  <div class="swatch-usage">错误提示背景</div>
                </div>
              </div>
              <div class="color-swatch danger-color">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">负面红</div>
                  <div class="swatch-hex">#E63757</div>
                  <div class="swatch-usage">跌幅、错误状态</div>
                </div>
              </div>
              <div class="color-swatch danger-color-dark">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">深红</div>
                  <div class="swatch-hex">#B91C1C</div>
                  <div class="swatch-usage">错误文本</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 中性色调 -->
          <div class="color-group">
            <h3 class="title-level-3">中性色调 - 辅助色</h3>
            <div class="color-swatches">
              <div class="color-swatch neutral-color-lighter">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">浅灰</div>
                  <div class="swatch-hex">#F8F9FA</div>
                  <div class="swatch-usage">背景色</div>
                </div>
              </div>
              <div class="color-swatch neutral-color-light">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">边框灰</div>
                  <div class="swatch-hex">#E4E7ED</div>
                  <div class="swatch-usage">边框、分割线</div>
                </div>
              </div>
              <div class="color-swatch neutral-color">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">次要文本</div>
                  <div class="swatch-hex">#909399</div>
                  <div class="swatch-usage">辅助信息</div>
                </div>
              </div>
              <div class="color-swatch neutral-color-dark">
                <div class="swatch-color"></div>
                <div class="swatch-info">
                  <div class="swatch-name">主要文本</div>
                  <div class="swatch-hex">#303133</div>
                  <div class="swatch-usage">正文内容</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 8px网格系统展示 -->
      <div class="grid-system-section">
        <h2 class="title-level-2">8px网格系统</h2>
        <p class="text-secondary">所有间距、尺寸均基于8px的倍数</p>
        
        <div class="grid-examples">
          <!-- 间距示例 -->
          <div class="grid-example">
            <h3 class="title-level-3">间距系统</h3>
            <div class="spacing-demo">
              <div class="spacing-item spacing-8">
                <div class="spacing-box"></div>
                <div class="spacing-label">8px - 最小间距</div>
              </div>
              <div class="spacing-item spacing-16">
                <div class="spacing-box"></div>
                <div class="spacing-label">16px - 元素间距</div>
              </div>
              <div class="spacing-item spacing-24">
                <div class="spacing-box"></div>
                <div class="spacing-label">24px - 组件间距</div>
              </div>
              <div class="spacing-item spacing-32">
                <div class="spacing-box"></div>
                <div class="spacing-label">32px - 区块间距</div>
              </div>
              <div class="spacing-item spacing-48">
                <div class="spacing-box"></div>
                <div class="spacing-label">48px - 章节间距</div>
              </div>
            </div>
          </div>

          <!-- 网格布局示例 -->
          <div class="grid-example">
            <h3 class="title-level-3">网格布局</h3>
            <div class="grid-layout-demo">
              <div class="grid-container">
                <div class="grid-item">网格项目 1</div>
                <div class="grid-item">网格项目 2</div>
                <div class="grid-item">网格项目 3</div>
                <div class="grid-item">网格项目 4</div>
                <div class="grid-item">网格项目 5</div>
                <div class="grid-item">网格项目 6</div>
              </div>
              <div class="grid-info">
                <div class="info-item">
                  <span class="info-label">间距：</span>
                  <span class="info-value">24px (3 × 8px)</span>
                </div>
                <div class="info-item">
                  <span class="info-label">内边距：</span>
                  <span class="info-value">16px (2 × 8px)</span>
                </div>
                <div class="info-item">
                  <span class="info-label">边框圆角：</span>
                  <span class="info-value">8px (1 × 8px)</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 组件尺寸示例 -->
          <div class="grid-example">
            <h3 class="title-level-3">组件尺寸</h3>
            <div class="component-sizes">
              <div class="size-demo">
                <div class="component-demo button-small">小按钮</div>
                <div class="size-label">高度: 32px (4 × 8px)</div>
              </div>
              <div class="size-demo">
                <div class="component-demo button-medium">中按钮</div>
                <div class="size-label">高度: 40px (5 × 8px)</div>
              </div>
              <div class="size-demo">
                <div class="component-demo button-large">大按钮</div>
                <div class="size-label">高度: 48px (6 × 8px)</div>
              </div>
              <div class="size-demo">
                <div class="component-demo input-demo">
                  <input type="text" placeholder="输入框示例" />
                </div>
                <div class="size-label">高度: 40px (5 × 8px)</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 三级字体系统展示 -->
      <div class="typography-section">
        <h2 class="title-level-2">三级字体系统</h2>
        <p class="text-secondary">清晰的字体层级确保信息传达的有效性</p>
        
        <div class="typography-examples">
          <!-- 字体层级 -->
          <div class="typography-example">
            <h3 class="title-level-3">字体层级</h3>
            <div class="font-hierarchy">
              <div class="font-level">
                <div class="font-sample title-level-1">一级标题 - 28px</div>
                <div class="font-info">
                  <div class="font-detail">字号: 28px</div>
                  <div class="font-detail">字重: 700 (Bold)</div>
                  <div class="font-detail">行高: 1.2</div>
                  <div class="font-detail">用途: 页面主标题</div>
                </div>
              </div>
              <div class="font-level">
                <div class="font-sample title-level-2">二级标题 - 24px</div>
                <div class="font-info">
                  <div class="font-detail">字号: 24px</div>
                  <div class="font-detail">字重: 600 (Semi Bold)</div>
                  <div class="font-detail">行高: 1.3</div>
                  <div class="font-detail">用途: 章节标题</div>
                </div>
              </div>
              <div class="font-level">
                <div class="font-sample title-level-3">三级标题 - 20px</div>
                <div class="font-info">
                  <div class="font-detail">字号: 20px</div>
                  <div class="font-detail">字重: 600 (Semi Bold)</div>
                  <div class="font-detail">行高: 1.4</div>
                  <div class="font-detail">用途: 子章节标题</div>
                </div>
              </div>
              <div class="font-level">
                <div class="font-sample text-primary">正文主要 - 16px</div>
                <div class="font-info">
                  <div class="font-detail">字号: 16px</div>
                  <div class="font-detail">字重: 400 (Regular)</div>
                  <div class="font-detail">行高: 1.6</div>
                  <div class="font-detail">用途: 主要内容</div>
                </div>
              </div>
              <div class="font-level">
                <div class="font-sample text-secondary">正文次要 - 14px</div>
                <div class="font-info">
                  <div class="font-detail">字号: 14px</div>
                  <div class="font-detail">字重: 400 (Regular)</div>
                  <div class="font-detail">行高: 1.5</div>
                  <div class="font-detail">用途: 辅助信息</div>
                </div>
              </div>
              <div class="font-level">
                <div class="font-sample text-small">小号文本 - 12px</div>
                <div class="font-info">
                  <div class="font-detail">字号: 12px</div>
                  <div class="font-detail">字重: 400 (Regular)</div>
                  <div class="font-detail">行高: 1.4</div>
                  <div class="font-detail">用途: 标签、说明</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 字体应用示例 -->
          <div class="typography-example">
            <h3 class="title-level-3">字体应用示例</h3>
            <div class="font-application">
              <div class="article-example">
                <h1 class="title-level-1">财经新闻分析报告</h1>
                <div class="article-meta">
                  <span class="text-small">发布时间: 2024-01-15</span>
                  <span class="text-small">作者: 数据分析师</span>
                  <span class="text-small">分类: 市场分析</span>
                </div>
                <h2 class="title-level-2">市场概况</h2>
                <p class="text-primary">
                  今日A股市场整体表现平稳，上证指数收盘上涨0.8%，深证成指上涨1.2%。
                  从行业表现来看，科技股继续领涨，新能源板块也有不俗表现。
                </p>
                <h3 class="title-level-3">重点关注</h3>
                <p class="text-secondary">
                  建议投资者重点关注以下几个方面的投资机会和风险点。
                </p>
                <div class="highlight-box">
                  <h4 class="text-primary">关键数据</h4>
                  <div class="data-grid">
                    <div class="data-item">
                      <div class="data-label text-small">上证指数</div>
                      <div class="data-value text-primary">3,124.56</div>
                      <div class="data-change success-text">+0.8%</div>
                    </div>
                    <div class="data-item">
                      <div class="data-label text-small">深证成指</div>
                      <div class="data-value text-primary">11,234.78</div>
                      <div class="data-change success-text">+1.2%</div>
                    </div>
                    <div class="data-item">
                      <div class="data-label text-small">创业板指</div>
                      <div class="data-value text-primary">2,456.89</div>
                      <div class="data-change danger-text">-0.3%</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 留白设计展示 -->
      <div class="whitespace-section">
        <h2 class="title-level-2">留白设计</h2>
        <p class="text-secondary">合理的留白设计提升阅读体验和视觉美感</p>
        
        <div class="whitespace-examples">
          <!-- 留白对比 -->
          <div class="whitespace-example">
            <h3 class="title-level-3">留白对比</h3>
            <div class="comparison-demo">
              <div class="comparison-item">
                <h4 class="text-primary">拥挤布局</h4>
                <div class="crowded-layout">
                  <div class="content-block">内容块1</div>
                  <div class="content-block">内容块2</div>
                  <div class="content-block">内容块3</div>
                  <div class="content-block">内容块4</div>
                  <div class="content-block">内容块5</div>
                  <div class="content-block">内容块6</div>
                </div>
              </div>
              <div class="comparison-item">
                <h4 class="text-primary">舒适布局</h4>
                <div class="comfortable-layout">
                  <div class="content-block">内容块1</div>
                  <div class="content-block">内容块2</div>
                  <div class="content-block">内容块3</div>
                  <div class="content-block">内容块4</div>
                  <div class="content-block">内容块5</div>
                  <div class="content-block">内容块6</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 留白应用 -->
          <div class="whitespace-example">
            <h3 class="title-level-3">留白应用</h3>
            <div class="whitespace-application">
              <div class="card-example">
                <div class="card-header">
                  <h4 class="text-primary">数据概览</h4>
                  <div class="card-actions">
                    <button class="action-button">刷新</button>
                    <button class="action-button">导出</button>
                  </div>
                </div>
                <div class="card-content">
                  <div class="metric-grid">
                    <div class="metric-item">
                      <div class="metric-label text-small">总用户数</div>
                      <div class="metric-value title-level-2">12,345</div>
                      <div class="metric-change success-text">+5.2%</div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-label text-small">活跃用户</div>
                      <div class="metric-value title-level-2">8,921</div>
                      <div class="metric-change success-text">+3.8%</div>
                    </div>
                    <div class="metric-item">
                      <div class="metric-label text-small">新增用户</div>
                      <div class="metric-value title-level-2">1,234</div>
                      <div class="metric-change danger-text">-1.5%</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 留白规则 -->
          <div class="whitespace-example">
            <h3 class="title-level-3">留白规则</h3>
            <div class="whitespace-rules">
              <div class="rule-item">
                <div class="rule-visual">
                  <div class="rule-demo minimum-whitespace">
                    <div class="demo-content">最小留白 ≥ 40px</div>
                  </div>
                </div>
                <div class="rule-description">
                  <div class="rule-title text-primary">最小留白</div>
                  <div class="rule-text text-secondary">
                    任何相邻元素之间的留白不少于40px，确保视觉呼吸空间
                  </div>
                </div>
              </div>
              <div class="rule-item">
                <div class="rule-visual">
                  <div class="rule-demo section-whitespace">
                    <div class="demo-content">章节留白 ≥ 80px</div>
                  </div>
                </div>
                <div class="rule-description">
                  <div class="rule-title text-primary">章节留白</div>
                  <div class="rule-text text-secondary">
                    不同章节之间的留白不少于80px，强化内容分组
                  </div>
                </div>
              </div>
              <div class="rule-item">
                <div class="rule-visual">
                  <div class="rule-demo content-whitespace">
                    <div class="demo-content">内容留白 ≥ 24px</div>
                  </div>
                </div>
                <div class="rule-description">
                  <div class="rule-title text-primary">内容留白</div>
                  <div class="rule-text text-secondary">
                    文本内容的行间距和段落间距保持适当留白
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'VisualHierarchy',
  setup() {
    onMounted(() => {
      ElMessage.success('视觉层次设计系统已加载完成')
    })

    return {}
  }
}
</script>

<style scoped>
/* 基础样式重置 */
* {
  box-sizing: border-box;
}

/* 主容器 */
.visual-hierarchy {
  min-height: 100vh;
  background: #f8f9fa;
  padding: 48px 24px;
}

.hierarchy-showcase {
  max-width: 1200px;
  margin: 0 auto;
}

/* 标题样式 */
.showcase-header {
  text-align: center;
  margin-bottom: 80px;
}

.showcase-header .title-level-1 {
  margin-bottom: 24px;
}

.showcase-header .description {
  font-size: 16px;
  color: #909399;
  margin: 0;
}

/* 三级字体系统 */
.title-level-1 {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  color: #1b4f72;
  margin: 0 0 24px 0;
}

.title-level-2 {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.3;
  color: #1b4f72;
  margin: 0 0 16px 0;
}

.title-level-3 {
  font-size: 20px;
  font-weight: 600;
  line-height: 1.4;
  color: #1b4f72;
  margin: 0 0 16px 0;
}

.text-primary {
  font-size: 16px;
  font-weight: 400;
  line-height: 1.6;
  color: #303133;
}

.text-secondary {
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
  color: #909399;
}

.text-small {
  font-size: 12px;
  font-weight: 400;
  line-height: 1.4;
  color: #909399;
}

/* 色彩类 */
.success-text {
  color: #00d97e;
}

.danger-text {
  color: #e63757;
}

/* 章节样式 */
.color-system-section,
.grid-system-section,
.typography-section,
.whitespace-section {
  margin-bottom: 80px;
  background: white;
  border-radius: 8px;
  padding: 48px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.color-system-section .title-level-2,
.grid-system-section .title-level-2,
.typography-section .title-level-2,
.whitespace-section .title-level-2 {
  border-bottom: 2px solid #2c7be5;
  padding-bottom: 16px;
  margin-bottom: 32px;
}

/* 色彩系统样式 */
.color-palette {
  display: flex;
  flex-direction: column;
  gap: 48px;
}

.color-group {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.color-swatches {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 24px;
}

.color-swatch {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.color-swatch:hover {
  transform: translateY(-4px);
}

.swatch-color {
  width: 100%;
  height: 80px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.swatch-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.swatch-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.swatch-hex {
  font-size: 14px;
  font-family: 'Courier New', monospace;
  color: #909399;
}

.swatch-usage {
  font-size: 12px;
  color: #606266;
}

/* 主色调 */
.primary-color-light .swatch-color {
  background: #e3f2fd;
}

.primary-color .swatch-color {
  background: #2c7be5;
}

.primary-color-dark .swatch-color {
  background: #1b4f72;
}

/* 成功色调 */
.success-color-light .swatch-color {
  background: #e8f5e8;
}

.success-color .swatch-color {
  background: #00d97e;
}

.success-color-dark .swatch-color {
  background: #007b4b;
}

/* 危险色调 */
.danger-color-light .swatch-color {
  background: #fee2e2;
}

.danger-color .swatch-color {
  background: #e63757;
}

.danger-color-dark .swatch-color {
  background: #b91c1c;
}

/* 中性色调 */
.neutral-color-lighter .swatch-color {
  background: #f8f9fa;
}

.neutral-color-light .swatch-color {
  background: #e4e7ed;
}

.neutral-color .swatch-color {
  background: #909399;
}

.neutral-color-dark .swatch-color {
  background: #303133;
}

/* 8px网格系统样式 */
.grid-examples {
  display: flex;
  flex-direction: column;
  gap: 48px;
}

.grid-example {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 间距示例 */
.spacing-demo {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.spacing-item {
  display: flex;
  align-items: center;
  gap: 24px;
}

.spacing-box {
  background: #2c7be5;
  border-radius: 4px;
}

.spacing-8 .spacing-box {
  width: 8px;
  height: 8px;
}

.spacing-16 .spacing-box {
  width: 16px;
  height: 16px;
}

.spacing-24 .spacing-box {
  width: 24px;
  height: 24px;
}

.spacing-32 .spacing-box {
  width: 32px;
  height: 32px;
}

.spacing-48 .spacing-box {
  width: 48px;
  height: 48px;
}

.spacing-label {
  font-size: 14px;
  color: #606266;
}

/* 网格布局示例 */
.grid-layout-demo {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
}

.grid-item {
  background: #e3f2fd;
  color: #1b4f72;
  padding: 16px;
  border-radius: 8px;
  text-align: center;
  font-weight: 500;
}

.grid-info {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-label {
  font-size: 14px;
  color: #909399;
}

.info-value {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

/* 组件尺寸示例 */
.component-sizes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
}

.size-demo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.component-demo {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #2c7be5;
  color: white;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.3s ease;
}

.component-demo:hover {
  background: #1b4f72;
}

.button-small {
  height: 32px;
  padding: 0 16px;
}

.button-medium {
  height: 40px;
  padding: 0 24px;
}

.button-large {
  height: 48px;
  padding: 0 32px;
}

.input-demo {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  width: 100%;
}

.input-demo input {
  width: 100%;
  height: 40px;
  padding: 0 16px;
  border: none;
  outline: none;
  font-size: 14px;
  color: #303133;
}

.size-label {
  font-size: 12px;
  color: #909399;
  text-align: center;
}

/* 字体系统样式 */
.typography-examples {
  display: flex;
  flex-direction: column;
  gap: 48px;
}

.typography-example {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.font-hierarchy {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.font-level {
  display: flex;
  align-items: center;
  gap: 48px;
  padding: 24px;
  background: #f8f9fa;
  border-radius: 8px;
}

.font-sample {
  flex: 1;
  margin: 0;
}

.font-info {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.font-detail {
  font-size: 12px;
  color: #909399;
}

/* 字体应用示例 */
.font-application {
  background: #f8f9fa;
  padding: 48px;
  border-radius: 8px;
}

.article-example {
  max-width: 800px;
  margin: 0 auto;
}

.article-meta {
  display: flex;
  gap: 24px;
  margin-bottom: 32px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e4e7ed;
}

.article-example p {
  margin: 0 0 24px 0;
}

.highlight-box {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 24px;
  margin-top: 32px;
}

.highlight-box h4 {
  margin: 0 0 16px 0;
}

.data-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 24px;
}

.data-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: center;
}

.data-label {
  margin: 0;
}

.data-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.data-change {
  font-size: 14px;
  font-weight: 500;
  margin: 0;
}

/* 留白设计样式 */
.whitespace-examples {
  display: flex;
  flex-direction: column;
  gap: 48px;
}

.whitespace-example {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 留白对比 */
.comparison-demo {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 48px;
}

.comparison-item {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comparison-item h4 {
  margin: 0;
  text-align: center;
}

.crowded-layout {
  background: #fee2e2;
  padding: 16px;
  border-radius: 8px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.comfortable-layout {
  background: #e8f5e8;
  padding: 48px;
  border-radius: 8px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.content-block {
  background: white;
  padding: 16px;
  border-radius: 8px;
  text-align: center;
  font-size: 14px;
  color: #303133;
}

/* 留白应用 */
.whitespace-application {
  display: flex;
  justify-content: center;
}

.card-example {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 600px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px;
  border-bottom: 1px solid #e4e7ed;
}

.card-header h4 {
  margin: 0;
}

.card-actions {
  display: flex;
  gap: 16px;
}

.action-button {
  padding: 8px 16px;
  background: #2c7be5;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.action-button:hover {
  background: #1b4f72;
}

.card-content {
  padding: 32px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 32px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: center;
}

.metric-label {
  margin: 0;
}

.metric-value {
  margin: 0;
}

.metric-change {
  font-size: 14px;
  font-weight: 500;
  margin: 0;
}

/* 留白规则 */
.whitespace-rules {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: 48px;
  padding: 24px;
  background: #f8f9fa;
  border-radius: 8px;
}

.rule-visual {
  flex: 1;
  display: flex;
  justify-content: center;
}

.rule-demo {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e3f2fd;
  border-radius: 8px;
  color: #1b4f72;
  font-weight: 500;
}

.minimum-whitespace {
  padding: 40px;
}

.section-whitespace {
  padding: 80px 40px;
}

.content-whitespace {
  padding: 24px;
}

.demo-content {
  white-space: nowrap;
}

.rule-description {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rule-title {
  margin: 0;
  font-weight: 600;
}

.rule-text {
  margin: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .visual-hierarchy {
    padding: 24px 16px;
  }
  
  .color-system-section,
  .grid-system-section,
  .typography-section,
  .whitespace-section {
    padding: 24px;
    margin-bottom: 48px;
  }
  
  .color-swatches {
    grid-template-columns: 1fr;
  }
  
  .grid-container {
    grid-template-columns: 1fr;
  }
  
  .component-sizes {
    grid-template-columns: 1fr;
  }
  
  .comparison-demo {
    grid-template-columns: 1fr;
  }
  
  .font-level {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
  
  .font-info {
    grid-template-columns: 1fr;
  }
  
  .rule-item {
    flex-direction: column;
    gap: 24px;
    text-align: center;
  }
  
  .article-meta {
    flex-direction: column;
    gap: 8px;
  }
  
  .data-grid {
    grid-template-columns: 1fr;
  }
  
  .metric-grid {
    grid-template-columns: 1fr;
  }
}
</style> 