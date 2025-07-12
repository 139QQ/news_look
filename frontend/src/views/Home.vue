<template>
  <div class="home">
    <h1>NewsLook 财经新闻系统</h1>
    <div class="welcome-content">
      <p>欢迎使用NewsLook财经新闻爬虫系统</p>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-card class="feature-card">
            <h3>实时采集</h3>
            <p>多源财经新闻实时采集</p>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="feature-card">
            <h3>智能分析</h3>
            <p>新闻内容智能分析处理</p>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card class="feature-card">
            <h3>数据展示</h3>
            <p>直观的数据可视化界面</p>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Home',
  data() {
    return {
      // 首页数据
    }
  }
}
</script>

<style scoped>
.home {
  padding: 20px;
}

.welcome-content {
  margin-top: 30px;
}

.feature-card {
  text-align: center;
  margin-bottom: 20px;
}

.feature-card h3 {
  color: #409EFF;
  margin-bottom: 15px;
}
</style> 