# 贡献指南

感谢您对本项目的关注！我们欢迎所有形式的贡献，包括但不限于：

- 代码贡献（新功能、错误修复）
- 文档改进
- Bug 报告
- 功能建议

## 1. 准备工作

### 1.1 环境设置

1. Fork 本代码库到您的 GitHub 账户
2. 克隆您 fork 的代码库到本地

```bash
git clone https://github.com/YOUR-USERNAME/finance_news_crawler.git
cd finance_news_crawler
```

3. 添加上游远程仓库

```bash
git remote add upstream https://github.com/ORIGINAL-OWNER/finance_news_crawler.git
```

4. 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装开发依赖
pip install -r requirements/dev.txt
```

### 1.2 开发工具设置

我们建议使用支持以下功能的IDE：

- Python 语法高亮和自动完成
- 对 Black 和 isort 的支持
- Pylint 或其他代码检查工具的集成

推荐的 IDE：
- VS Code（带有 Python 扩展）
- PyCharm

确保将编辑器配置为使用项目的 `.editorconfig` 文件：

```
root = true

[*]
end_of_line = lf
insert_final_newline = true
charset = utf-8
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{json,yml,yaml}]
indent_size = 2

[*.md]
trim_trailing_whitespace = false
```

## 2. 开发流程

### 2.1 选择任务

- 查看 Issues 列表，寻找带有 "good first issue" 标签的问题
- 如果您想实现一个尚未在 Issues 中的新功能，请先创建一个 Issue 描述您的想法

### 2.2 创建分支

从最新的主分支创建一个新的分支：

```bash
# 确保本地分支是最新的
git checkout main
git pull upstream main

# 创建新分支
git checkout -b feature/your-feature-name
# 或者
git checkout -b fix/issue-description
```

### 2.3 编写代码

- 遵循项目的编码规范（参见 [编码规范](coding_style.md)）
- 确保为新功能或修复添加相应的测试
- 定期提交更改，保持提交消息清晰

### 2.4 测试

在提交 PR 之前，请确保：

1. 所有测试都能通过

```bash
pytest
```

2. 代码符合项目的质量标准

```bash
# 运行代码格式化工具
black .
isort .

# 运行代码检查工具
pylint app tests
mypy app
```

3. 如果添加了新功能，请确保编写了相关文档

### 2.5 提交更改

```bash
git add .
git commit -m "feat: 添加了新的爬虫功能"
git push origin feature/your-feature-name
```

### 2.6 创建 Pull Request

1. 在 GitHub 上导航到您的分支
2. 点击 "Compare & pull request" 按钮
3. 填写 PR 标题和描述，详细说明您的更改
4. 如果您的 PR 解决了一个 Issue，请在描述中使用 "Fixes #123" 语法进行关联
5. 选择仓库维护者作为 reviewers
6. 提交 PR

## 3. 代码审查

当您提交 PR 后，可能会收到一些反馈和修改建议：

1. 保持积极的态度，代码审查的目的是提高代码质量
2. 及时回应评论并进行必要的修改
3. 提交修改后，通知审查人员重新审查
4. 当 PR 被批准后，它将被合并到主分支

## 4. 报告 Bug

如果您发现了一个 bug 但没有时间或能力修复它，请通过创建 Issue 报告它：

1. 使用清晰的标题描述问题
2. 提供复现问题的详细步骤
3. 描述预期行为和实际行为
4. 如果可能，包括错误日志、截图或相关信息
5. 指定您的操作系统和 Python 版本

## 5. 提出建议

对于功能建议，请创建一个 Issue：

1. 清晰地描述您想要的功能
2. 解释为什么这个功能对项目有益
3. 如果可能，提供一些实现思路或伪代码

## 6. 文档贡献

文档改进同样重要：

1. 修复文档中的错误或不明确的部分
2. 为现有功能添加更多的使用示例
3. 改进安装或配置说明
4. 翻译文档（如果适用）

## 7. 社区准则

为了保持积极和包容的社区环境，请：

- 尊重其他贡献者
- 给予和接受建设性的反馈
- 专注于问题而不是个人
- 耐心对待新贡献者

感谢您的贡献，我们期待与您合作！ 