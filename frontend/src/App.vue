<template>
  <div id="app">
    <ErrorBoundary>
      <Layout />
      <NetworkStatus />
    </ErrorBoundary>
  </div>
</template>

<script setup>
import ErrorBoundary from '@/components/ErrorBoundary.vue'
import NetworkStatus from '@/components/NetworkStatus.vue'
import Layout from '@/components/Layout.vue'

// 应用根组件
</script>

<style>
#app {
  min-height: 100vh;
  width: 100%;
  position: relative;
  overflow: visible;
  /* 强制确保app容器可见 */
  background-color: #f5f5f5;
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  z-index: auto;
}

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  overflow-x: hidden;
}

* {
  box-sizing: border-box;
}

/* 确保Element Plus组件层级正常 */
.el-message {
  z-index: 3000 !important;
}

.el-loading-mask {
  z-index: 2000 !important;
}

.el-overlay {
  z-index: 2000 !important;
}
</style> 