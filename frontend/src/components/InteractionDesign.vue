<template>
  <div class="interaction-design">
    <!-- 交互设计展示区域 -->
    <div class="interaction-showcase">
      <div class="showcase-header">
        <h2>交互设计展示</h2>
        <p>演示反馈机制、操作路径优化和容错设计</p>
      </div>

      <!-- 即时反馈示例 -->
      <div class="feedback-section">
        <h3>即时反馈机制</h3>
        <div class="feedback-demos">
          <!-- 表单验证反馈 -->
          <div class="demo-card">
            <h4>表单验证反馈</h4>
            <el-form :model="formData" :rules="formRules" ref="formRef" label-width="100px">
              <el-form-item label="用户名" prop="username">
                <el-input
                  v-model="formData.username"
                  placeholder="请输入用户名"
                  @blur="validateUsername"
                  :class="{ 'input-success': formData.username && !formErrors.username }"
                >
                  <template #suffix>
                    <el-icon v-if="formData.username && !formErrors.username" class="success-icon">
                      <Check />
                    </el-icon>
                    <el-icon v-else-if="formErrors.username" class="error-icon">
                      <Close />
                    </el-icon>
                  </template>
                </el-input>
                <div v-if="formErrors.username" class="error-message">
                  {{ formErrors.username }}
                </div>
              </el-form-item>
              
              <el-form-item label="密码" prop="password">
                <el-input
                  v-model="formData.password"
                  type="password"
                  placeholder="请输入密码"
                  @input="checkPasswordStrength"
                  show-password
                >
                  <template #suffix>
                    <div class="password-strength" :class="passwordStrength.level">
                      {{ passwordStrength.text }}
                    </div>
                  </template>
                </el-input>
                <div class="password-strength-bar">
                  <div 
                    class="strength-indicator" 
                    :class="passwordStrength.level"
                    :style="{ width: passwordStrength.percentage + '%' }"
                  ></div>
                </div>
              </el-form-item>
            </el-form>
          </div>

          <!-- 加载状态反馈 -->
          <div class="demo-card">
            <h4>加载状态反馈</h4>
            <div class="loading-demos">
              <el-button 
                @click="simulateOperation('save')"
                :loading="loadingStates.save"
                type="primary"
              >
                {{ loadingStates.save ? '保存中...' : '保存数据' }}
              </el-button>
              
              <el-button 
                @click="simulateOperation('delete')"
                :loading="loadingStates.delete"
                type="danger"
              >
                {{ loadingStates.delete ? '删除中...' : '删除数据' }}
              </el-button>
              
              <el-button 
                @click="simulateOperation('export')"
                :loading="loadingStates.export"
                type="success"
              >
                {{ loadingStates.export ? '导出中...' : '导出报告' }}
              </el-button>
            </div>
          </div>

          <!-- 操作结果反馈 -->
          <div class="demo-card">
            <h4>操作结果反馈</h4>
            <div class="result-demos">
              <el-button @click="showSuccessMessage" type="success">成功消息</el-button>
              <el-button @click="showWarningMessage" type="warning">警告消息</el-button>
              <el-button @click="showErrorMessage" type="danger">错误消息</el-button>
              <el-button @click="showInfoMessage" type="info">信息消息</el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 操作路径优化示例 -->
      <div class="operation-path-section">
        <h3>操作路径优化 (≤3步)</h3>
        <div class="path-demos">
          <!-- 单步操作 -->
          <div class="demo-card">
            <h4>单步操作</h4>
            <div class="single-step-demo">
              <el-button @click="oneStepOperation" type="primary">
                <el-icon><Plus /></el-icon>
                一键添加新闻源
              </el-button>
              <el-button @click="oneStepOperation" type="success">
                <el-icon><Download /></el-icon>
                一键导出数据
              </el-button>
              <el-button @click="oneStepOperation" type="warning">
                <el-icon><RefreshRight /></el-icon>
                一键刷新状态
              </el-button>
            </div>
          </div>

          <!-- 两步操作 -->
          <div class="demo-card">
            <h4>两步操作</h4>
            <div class="two-step-demo">
              <div class="step-indicator">
                <div class="step" :class="{ active: twoStepProgress >= 1, completed: twoStepProgress > 1 }">
                  <div class="step-number">1</div>
                  <div class="step-label">选择配置</div>
                </div>
                <div class="step-line" :class="{ active: twoStepProgress > 1 }"></div>
                <div class="step" :class="{ active: twoStepProgress >= 2, completed: twoStepProgress > 2 }">
                  <div class="step-number">2</div>
                  <div class="step-label">确认执行</div>
                </div>
              </div>
              <div class="step-content">
                <div v-if="twoStepProgress === 0" class="step-start">
                  <el-button @click="startTwoStepOperation" type="primary">
                    开始配置爬虫
                  </el-button>
                </div>
                <div v-else-if="twoStepProgress === 1" class="step-config">
                  <el-select v-model="selectedConfig" placeholder="选择配置模板">
                    <el-option label="财经新闻配置" value="finance" />
                    <el-option label="股票数据配置" value="stock" />
                    <el-option label="期货数据配置" value="futures" />
                  </el-select>
                  <el-button @click="confirmTwoStepOperation" type="success">
                    确认配置
                  </el-button>
                </div>
                <div v-else-if="twoStepProgress === 2" class="step-complete">
                  <el-icon class="success-icon-large"><CircleCheck /></el-icon>
                  <p>配置完成！</p>
                  <el-button @click="resetTwoStepOperation" type="info">
                    重新配置
                  </el-button>
                </div>
              </div>
            </div>
          </div>

          <!-- 三步操作 -->
          <div class="demo-card">
            <h4>三步操作</h4>
            <div class="three-step-demo">
              <div class="step-indicator">
                <div class="step" :class="{ active: threeStepProgress >= 1, completed: threeStepProgress > 1 }">
                  <div class="step-number">1</div>
                  <div class="step-label">选择数据</div>
                </div>
                <div class="step-line" :class="{ active: threeStepProgress > 1 }"></div>
                <div class="step" :class="{ active: threeStepProgress >= 2, completed: threeStepProgress > 2 }">
                  <div class="step-number">2</div>
                  <div class="step-label">设置参数</div>
                </div>
                <div class="step-line" :class="{ active: threeStepProgress > 2 }"></div>
                <div class="step" :class="{ active: threeStepProgress >= 3, completed: threeStepProgress > 3 }">
                  <div class="step-number">3</div>
                  <div class="step-label">生成报告</div>
                </div>
              </div>
              <div class="step-content">
                <div v-if="threeStepProgress === 0" class="step-start">
                  <el-button @click="startThreeStepOperation" type="primary">
                    开始数据分析
                  </el-button>
                </div>
                <div v-else-if="threeStepProgress === 1" class="step-data">
                  <el-checkbox-group v-model="selectedData">
                    <el-checkbox label="stock">股票数据</el-checkbox>
                    <el-checkbox label="news">新闻数据</el-checkbox>
                    <el-checkbox label="futures">期货数据</el-checkbox>
                  </el-checkbox-group>
                  <el-button @click="nextThreeStepOperation" type="primary">
                    下一步
                  </el-button>
                </div>
                <div v-else-if="threeStepProgress === 2" class="step-params">
                  <el-form :model="analysisParams" label-width="100px">
                    <el-form-item label="时间范围">
                      <el-select v-model="analysisParams.timeRange">
                        <el-option label="最近7天" value="7d" />
                        <el-option label="最近30天" value="30d" />
                        <el-option label="最近90天" value="90d" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="分析类型">
                      <el-select v-model="analysisParams.type">
                        <el-option label="趋势分析" value="trend" />
                        <el-option label="情感分析" value="sentiment" />
                        <el-option label="关联分析" value="correlation" />
                      </el-select>
                    </el-form-item>
                  </el-form>
                  <el-button @click="finishThreeStepOperation" type="success">
                    生成报告
                  </el-button>
                </div>
                <div v-else-if="threeStepProgress === 3" class="step-complete">
                  <el-icon class="success-icon-large"><CircleCheck /></el-icon>
                  <p>报告生成完成！</p>
                  <el-button @click="resetThreeStepOperation" type="info">
                    重新分析
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 容错设计示例 -->
      <div class="error-handling-section">
        <h3>容错设计</h3>
        <div class="error-demos">
          <!-- 网络错误处理 -->
          <div class="demo-card">
            <h4>网络错误处理</h4>
            <div class="network-error-demo">
              <el-button @click="simulateNetworkError" type="primary">
                模拟网络请求
              </el-button>
              <div v-if="networkError" class="error-state">
                <div class="error-illustration">
                  <el-icon class="error-icon-large"><Connection /></el-icon>
                </div>
                <div class="error-content">
                  <h4>网络连接失败</h4>
                  <p>请检查网络连接后重试</p>
                  <div class="error-actions">
                    <el-button @click="retryNetworkRequest" type="primary">
                      重试
                    </el-button>
                    <el-button @click="clearNetworkError" type="info">
                      取消
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 数据验证错误 -->
          <div class="demo-card">
            <h4>数据验证错误</h4>
            <div class="validation-error-demo">
              <el-form :model="validationForm" ref="validationFormRef">
                <el-form-item>
                  <el-input
                    v-model="validationForm.email"
                    placeholder="请输入邮箱地址"
                    @blur="validateEmail"
                    :class="{ 'input-error': validationErrors.email }"
                  >
                    <template #prepend>邮箱</template>
                  </el-input>
                  <div v-if="validationErrors.email" class="error-message">
                    {{ validationErrors.email }}
                  </div>
                </el-form-item>
                <el-form-item>
                  <el-input
                    v-model="validationForm.phone"
                    placeholder="请输入手机号码"
                    @blur="validatePhone"
                    :class="{ 'input-error': validationErrors.phone }"
                  >
                    <template #prepend>手机</template>
                  </el-input>
                  <div v-if="validationErrors.phone" class="error-message">
                    {{ validationErrors.phone }}
                  </div>
                </el-form-item>
              </el-form>
            </div>
          </div>

          <!-- 系统错误处理 -->
          <div class="demo-card">
            <h4>系统错误处理</h4>
            <div class="system-error-demo">
              <el-button @click="simulateSystemError" type="danger">
                模拟系统错误
              </el-button>
              <div v-if="systemError" class="error-state">
                <div class="error-illustration">
                  <el-icon class="error-icon-large"><Warning /></el-icon>
                </div>
                <div class="error-content">
                  <h4>系统错误</h4>
                  <p>系统遇到了一个未知错误，请稍后重试</p>
                  <div class="error-details">
                    <el-collapse v-model="errorDetailsVisible">
                      <el-collapse-item title="错误详情" name="1">
                        <div class="error-detail-text">
                          错误代码: {{ systemError.code }}<br>
                          错误信息: {{ systemError.message }}<br>
                          发生时间: {{ systemError.timestamp }}
                        </div>
                      </el-collapse-item>
                    </el-collapse>
                  </div>
                  <div class="error-actions">
                    <el-button @click="reportError" type="primary">
                      报告错误
                    </el-button>
                    <el-button @click="clearSystemError" type="info">
                      关闭
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 优雅降级示例 -->
          <div class="demo-card">
            <h4>优雅降级</h4>
            <div class="graceful-degradation-demo">
              <el-switch
                v-model="featureEnabled"
                active-text="高级功能"
                inactive-text="基础功能"
                @change="toggleFeature"
              />
              <div v-if="featureEnabled" class="advanced-feature">
                <h5>高级数据可视化</h5>
                <div class="chart-placeholder">
                  <el-icon class="chart-icon"><TrendCharts /></el-icon>
                  <p>交互式图表加载中...</p>
                </div>
              </div>
              <div v-else class="basic-feature">
                <h5>基础数据展示</h5>
                <el-table :data="basicData" style="width: 100%">
                  <el-table-column prop="name" label="名称" />
                  <el-table-column prop="value" label="值" />
                </el-table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Check, Close, Plus, Download, RefreshRight, CircleCheck, Connection, Warning, TrendCharts } from '@element-plus/icons-vue'

export default {
  name: 'InteractionDesign',
  components: {
    Check,
    Close,
    Plus,
    Download,
    RefreshRight,
    CircleCheck,
    Connection,
    Warning,
    TrendCharts
  },
  setup() {
    // 表单数据
    const formData = reactive({
      username: '',
      password: ''
    })

    const formErrors = reactive({
      username: '',
      password: ''
    })

    const formRules = {
      username: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { min: 3, max: 20, message: '用户名长度在3到20个字符', trigger: 'blur' }
      ],
      password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, message: '密码长度至少6个字符', trigger: 'blur' }
      ]
    }

    // 加载状态
    const loadingStates = reactive({
      save: false,
      delete: false,
      export: false
    })

    // 密码强度
    const passwordStrength = ref({
      level: 'weak',
      text: '弱',
      percentage: 0
    })

    // 两步操作状态
    const twoStepProgress = ref(0)
    const selectedConfig = ref('')

    // 三步操作状态
    const threeStepProgress = ref(0)
    const selectedData = ref([])
    const analysisParams = reactive({
      timeRange: '30d',
      type: 'trend'
    })

    // 错误处理状态
    const networkError = ref(false)
    const systemError = ref(null)
    const errorDetailsVisible = ref([])

    // 验证表单
    const validationForm = reactive({
      email: '',
      phone: ''
    })

    const validationErrors = reactive({
      email: '',
      phone: ''
    })

    // 优雅降级
    const featureEnabled = ref(true)
    const basicData = ref([
      { name: '用户数', value: '1,234' },
      { name: '新闻数', value: '5,678' },
      { name: '访问量', value: '9,012' }
    ])

    // 表单验证方法
    const validateUsername = () => {
      if (!formData.username) {
        formErrors.username = '用户名不能为空'
      } else if (formData.username.length < 3) {
        formErrors.username = '用户名长度至少3个字符'
      } else if (formData.username.length > 20) {
        formErrors.username = '用户名长度不能超过20个字符'
      } else {
        formErrors.username = ''
      }
    }

    const checkPasswordStrength = () => {
      const password = formData.password
      if (!password) {
        passwordStrength.value = { level: 'weak', text: '弱', percentage: 0 }
        return
      }

      let score = 0
      let text = '弱'
      let level = 'weak'

      // 长度检查
      if (password.length >= 6) score += 1
      if (password.length >= 8) score += 1
      if (password.length >= 12) score += 1

      // 复杂度检查
      if (/[a-z]/.test(password)) score += 1
      if (/[A-Z]/.test(password)) score += 1
      if (/[0-9]/.test(password)) score += 1
      if (/[^a-zA-Z0-9]/.test(password)) score += 1

      if (score >= 6) {
        level = 'strong'
        text = '强'
      } else if (score >= 4) {
        level = 'medium'
        text = '中'
      }

      passwordStrength.value = {
        level,
        text,
        percentage: Math.min(100, (score / 7) * 100)
      }
    }

    // 模拟操作
    const simulateOperation = (type) => {
      loadingStates[type] = true
      setTimeout(() => {
        loadingStates[type] = false
        ElMessage.success(`${type}操作完成！`)
      }, 2000)
    }

    // 消息提示
    const showSuccessMessage = () => {
      ElMessage({
        message: '操作成功完成！',
        type: 'success',
        duration: 3000,
        showClose: true
      })
    }

    const showWarningMessage = () => {
      ElMessage({
        message: '请注意：此操作可能影响系统性能',
        type: 'warning',
        duration: 4000,
        showClose: true
      })
    }

    const showErrorMessage = () => {
      ElMessage({
        message: '操作失败：权限不足',
        type: 'error',
        duration: 5000,
        showClose: true
      })
    }

    const showInfoMessage = () => {
      ElNotification({
        title: '系统通知',
        message: '数据同步已完成，共更新了1,234条记录',
        type: 'info',
        duration: 6000,
        position: 'top-right'
      })
    }

    // 一步操作
    const oneStepOperation = () => {
      ElMessage.success('操作完成！只需要一步就搞定了')
    }

    // 两步操作
    const startTwoStepOperation = () => {
      twoStepProgress.value = 1
    }

    const confirmTwoStepOperation = () => {
      if (!selectedConfig.value) {
        ElMessage.warning('请选择配置模板')
        return
      }
      twoStepProgress.value = 2
      setTimeout(() => {
        ElMessage.success('配置已保存')
      }, 1000)
    }

    const resetTwoStepOperation = () => {
      twoStepProgress.value = 0
      selectedConfig.value = ''
    }

    // 三步操作
    const startThreeStepOperation = () => {
      threeStepProgress.value = 1
    }

    const nextThreeStepOperation = () => {
      if (selectedData.value.length === 0) {
        ElMessage.warning('请至少选择一种数据类型')
        return
      }
      threeStepProgress.value = 2
    }

    const finishThreeStepOperation = () => {
      threeStepProgress.value = 3
      setTimeout(() => {
        ElMessage.success('报告生成完成')
      }, 1000)
    }

    const resetThreeStepOperation = () => {
      threeStepProgress.value = 0
      selectedData.value = []
      analysisParams.timeRange = '30d'
      analysisParams.type = 'trend'
    }

    // 错误处理
    const simulateNetworkError = () => {
      networkError.value = true
      setTimeout(() => {
        // 模拟网络超时
      }, 100)
    }

    const retryNetworkRequest = () => {
      networkError.value = false
      ElMessage.success('网络请求重试成功')
    }

    const clearNetworkError = () => {
      networkError.value = false
    }

    const simulateSystemError = () => {
      systemError.value = {
        code: 'SYS_ERROR_500',
        message: '内部服务器错误',
        timestamp: new Date().toLocaleString()
      }
    }

    const reportError = () => {
      ElMessage.success('错误报告已提交，感谢您的反馈')
      clearSystemError()
    }

    const clearSystemError = () => {
      systemError.value = null
      errorDetailsVisible.value = []
    }

    // 验证方法
    const validateEmail = () => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
      if (!validationForm.email) {
        validationErrors.email = '请输入邮箱地址'
      } else if (!emailRegex.test(validationForm.email)) {
        validationErrors.email = '请输入有效的邮箱地址'
      } else {
        validationErrors.email = ''
      }
    }

    const validatePhone = () => {
      const phoneRegex = /^1[3-9]\d{9}$/
      if (!validationForm.phone) {
        validationErrors.phone = '请输入手机号码'
      } else if (!phoneRegex.test(validationForm.phone)) {
        validationErrors.phone = '请输入有效的手机号码'
      } else {
        validationErrors.phone = ''
      }
    }

    // 优雅降级
    const toggleFeature = (enabled) => {
      if (enabled) {
        ElMessage.info('正在加载高级功能...')
      } else {
        ElMessage.info('已切换到基础功能模式')
      }
    }

    onMounted(() => {
      ElMessage.success('交互设计组件已加载完成')
    })

    return {
      formData,
      formErrors,
      formRules,
      loadingStates,
      passwordStrength,
      twoStepProgress,
      selectedConfig,
      threeStepProgress,
      selectedData,
      analysisParams,
      networkError,
      systemError,
      errorDetailsVisible,
      validationForm,
      validationErrors,
      featureEnabled,
      basicData,
      validateUsername,
      checkPasswordStrength,
      simulateOperation,
      showSuccessMessage,
      showWarningMessage,
      showErrorMessage,
      showInfoMessage,
      oneStepOperation,
      startTwoStepOperation,
      confirmTwoStepOperation,
      resetTwoStepOperation,
      startThreeStepOperation,
      nextThreeStepOperation,
      finishThreeStepOperation,
      resetThreeStepOperation,
      simulateNetworkError,
      retryNetworkRequest,
      clearNetworkError,
      simulateSystemError,
      reportError,
      clearSystemError,
      validateEmail,
      validatePhone,
      toggleFeature
    }
  }
}
</script>

<style scoped>
.interaction-design {
  min-height: 100vh;
  background: #f5f7fa;
  padding: 24px;
}

.interaction-showcase {
  max-width: 1200px;
  margin: 0 auto;
}

.showcase-header {
  text-align: center;
  margin-bottom: 40px;
}

.showcase-header h2 {
  font-size: 28px;
  color: #303133;
  margin-bottom: 16px;
}

.showcase-header p {
  font-size: 16px;
  color: #606266;
  margin: 0;
}

.feedback-section,
.operation-path-section,
.error-handling-section {
  margin-bottom: 48px;
}

.feedback-section h3,
.operation-path-section h3,
.error-handling-section h3 {
  font-size: 24px;
  color: #303133;
  margin-bottom: 24px;
  border-bottom: 2px solid #409eff;
  padding-bottom: 8px;
}

.feedback-demos,
.path-demos,
.error-demos {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
}

.demo-card {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.demo-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
}

.demo-card h4 {
  font-size: 18px;
  color: #303133;
  margin-bottom: 16px;
  border-left: 4px solid #409eff;
  padding-left: 12px;
}

/* 表单验证样式 */
.input-success {
  border-color: #67c23a;
}

.input-error {
  border-color: #f56c6c;
}

.success-icon {
  color: #67c23a;
}

.error-icon {
  color: #f56c6c;
}

.error-message {
  color: #f56c6c;
  font-size: 12px;
  margin-top: 4px;
}

.password-strength {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.password-strength.weak {
  background: #fef0f0;
  color: #f56c6c;
}

.password-strength.medium {
  background: #fdf6ec;
  color: #e6a23c;
}

.password-strength.strong {
  background: #f0f9ff;
  color: #67c23a;
}

.password-strength-bar {
  width: 100%;
  height: 4px;
  background: #f5f7fa;
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}

.strength-indicator {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 2px;
}

.strength-indicator.weak {
  background: #f56c6c;
}

.strength-indicator.medium {
  background: #e6a23c;
}

.strength-indicator.strong {
  background: #67c23a;
}

/* 加载状态样式 */
.loading-demos {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.result-demos {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

/* 步骤指示器样式 */
.step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f5f7fa;
  color: #909399;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  transition: all 0.3s ease;
}

.step.active .step-number {
  background: #409eff;
  color: white;
}

.step.completed .step-number {
  background: #67c23a;
  color: white;
}

.step-label {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
  text-align: center;
}

.step.active .step-label {
  color: #409eff;
  font-weight: 600;
}

.step.completed .step-label {
  color: #67c23a;
}

.step-line {
  width: 60px;
  height: 2px;
  background: #f5f7fa;
  transition: background 0.3s ease;
}

.step-line.active {
  background: #409eff;
}

.step-content {
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 16px;
}

.step-complete {
  text-align: center;
}

.success-icon-large {
  font-size: 48px;
  color: #67c23a;
  margin-bottom: 16px;
}

/* 错误处理样式 */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 32px;
  background: #fef0f0;
  border-radius: 8px;
  border: 1px solid #fbc4c4;
  margin-top: 16px;
}

.error-illustration {
  margin-bottom: 16px;
}

.error-icon-large {
  font-size: 48px;
  color: #f56c6c;
}

.error-content h4 {
  font-size: 18px;
  color: #303133;
  margin-bottom: 8px;
}

.error-content p {
  color: #606266;
  margin-bottom: 16px;
}

.error-actions {
  display: flex;
  gap: 12px;
}

.error-details {
  width: 100%;
  margin: 16px 0;
}

.error-detail-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #909399;
  background: #f8f9fa;
  padding: 12px;
  border-radius: 4px;
  text-align: left;
}

/* 优雅降级样式 */
.graceful-degradation-demo {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.advanced-feature,
.basic-feature {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #f8f9fa;
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
}

.chart-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .interaction-design {
    padding: 16px;
  }
  
  .feedback-demos,
  .path-demos,
  .error-demos {
    grid-template-columns: 1fr;
  }
  
  .demo-card {
    padding: 16px;
  }
  
  .loading-demos,
  .result-demos {
    flex-direction: column;
  }
  
  .step-indicator {
    flex-direction: column;
    gap: 16px;
  }
  
  .step-line {
    width: 2px;
    height: 30px;
  }
}
</style> 