# Sass 现代API升级指南

## 问题背景

NewsLook项目在构建过程中出现以下弃用警告：

```
Deprecation Warning [legacy-js-api]: The legacy JS API is deprecated and will be removed in Dart Sass 2.0.0.
```

这是因为项目使用的是基于Node Sass的旧版API，该API在Dart Sass 1.45.0中被现代API取代，并将在Dart Sass 2.0.0中完全移除。

## 解决方案

### 1. 升级Sass版本

已将Sass版本从`1.69.5`升级到`1.77.0`，并添加了`sass-embedded`作为现代编译器：

```json
{
  "devDependencies": {
    "sass": "^1.77.0",
    "sass-embedded": "^1.77.0"
  }
}
```

### 2. 更新Vite配置

在`vite.config.js`中更新了SCSS配置：

```javascript
css: {
  preprocessorOptions: {
    scss: {
      // 静默弃用警告
      silenceDeprecations: ['legacy-js-api'],
      // 移除全局导入，避免与@use规则冲突
      additionalData: ''
    }
  }
}
```

### 3. 关键配置项说明

- **silenceDeprecations**: 静默特定的弃用警告
- **additionalData**: 空字符串，避免与现代`@use`规则冲突
- **sass-embedded**: 提供更好的性能和现代API支持

## 升级步骤

### 方式1：自动更新脚本

```bash
cd frontend
npm run update-sass
```

### 方式2：手动更新

```bash
cd frontend

# 1. 清理现有依赖
rm -rf node_modules package-lock.json

# 2. 重新安装依赖
npm install

# 3. 验证Sass版本
npm list sass sass-embedded
```

## 验证升级结果

1. **检查版本**：
   ```bash
   npm list sass sass-embedded
   ```

2. **启动开发服务器**：
   ```bash
   npm run dev
   ```

3. **确认无警告**：
   启动后不应再看到`[legacy-js-api]`相关的弃用警告。

## 现代Sass最佳实践

### 1. 使用@use替代@import

**推荐（现代）**：
```scss
@use '@/styles/variables.scss' as *;
@use '@/styles/mixins.scss' as mixins;
```

**避免（弃用）**：
```scss
@import '@/styles/variables.scss';
@import '@/styles/mixins.scss';
```

### 2. 模块化CSS架构

```
src/styles/
├── variables.scss    # 变量定义
├── mixins.scss      # 混入函数
├── base.scss        # 基础样式
└── components/      # 组件样式
    ├── button.scss
    └── card.scss
```

### 3. 性能优化

- 使用`sass-embedded`获得更好的编译性能
- 避免在全局范围内导入大量样式
- 使用CSS模块化避免样式冲突

## 常见问题解决

### Q: 升级后出现样式丢失？
A: 检查是否有组件依赖全局样式导入，需要手动添加`@use`语句。

### Q: 编译速度变慢？
A: 确保已安装`sass-embedded`，它提供更好的性能。

### Q: 仍有弃用警告？
A: 检查是否有第三方包使用旧API，可能需要更新相关依赖。

## 相关资源

- [Sass现代API文档](https://sass-lang.com/documentation/js-api)
- [Vite CSS预处理器配置](https://vitejs.dev/config/shared-options.html#css-preprocessoroptions)
- [sass-embedded性能说明](https://sass-lang.com/blog/embedded-protocol)

## 后续维护

1. 定期更新Sass版本到最新稳定版
2. 监控Sass官方弃用通知
3. 逐步迁移旧的`@import`语句到`@use`
4. 优化CSS模块化结构 