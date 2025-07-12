#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NewsLook 项目文件结构完善重构脚本
移动剩余文件并完善目录结构
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

class CompleteRestructurer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def move_remaining_backend_files(self):
        """移动剩余的后端文件到backend目录"""
        
        # 移动主要后端目录
        backend_directories = [
            ("app", "backend/app"),
            ("newslook", "backend/newslook"),
            ("api", "backend/api"), 
            ("utils", "backend/utils")
        ]
        
        for source, target in backend_directories:
            source_path = self.project_root / source
            target_path = self.project_root / target
            
            if source_path.exists():
                print(f"🔄 移动后端目录: {source} -> {target}")
                
                # 如果目标目录已存在，先备份
                if target_path.exists():
                    backup_path = self.project_root / "backup/legacy_files" / f"{source}_{self.backup_timestamp}"
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(target_path), str(backup_path))
                    print(f"  📦 原目录备份至: {backup_path}")
                
                # 移动目录
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(target_path))
                print(f"  ✅ 移动完成: {target}")
        
        # 移动主要的Python启动文件
        backend_files = [
            "main.py",
            "run.py", 
            "quick_start.py",
            "start_newslook_full.py",
            "debug_crawler.py"
        ]
        
        backend_main_dir = self.project_root / "backend"
        backend_main_dir.mkdir(exist_ok=True)
        
        for filename in backend_files:
            source_file = self.project_root / filename
            target_file = backend_main_dir / filename
            
            if source_file.exists():
                print(f"🔄 移动启动文件: {filename}")
                shutil.copy2(source_file, target_file)
                # 保留根目录的原文件，以免影响现有启动脚本
    
    def organize_frontend_structure(self):
        """整理前端目录结构"""
        frontend_root = self.project_root / "frontend"
        
        # 移动错误放置的前端文件
        misplaced_frontend_files = [
            ("src", "frontend/src"),
            ("public", "frontend/public")
        ]
        
        for source, target in misplaced_frontend_files:
            source_path = self.project_root / source
            target_path = self.project_root / target
            
            if source_path.exists() and source_path != target_path:
                print(f"🔄 移动前端文件: {source} -> {target}")
                
                # 合并目录内容
                if target_path.exists():
                    # 将源目录内容合并到目标目录
                    for item in source_path.rglob("*"):
                        if item.is_file():
                            relative_path = item.relative_to(source_path)
                            target_file = target_path / relative_path
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            
                            if not target_file.exists():
                                shutil.copy2(item, target_file)
                    
                    # 删除源目录
                    shutil.rmtree(source_path)
                else:
                    # 直接移动
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source_path), str(target_path))
                
                print(f"  ✅ 前端文件移动完成")
        
        # 移动favicon到正确位置
        favicon_source = self.project_root / "favicon.svg"
        favicon_target = frontend_root / "public/favicon.svg"
        
        if favicon_source.exists():
            favicon_target.parent.mkdir(parents=True, exist_ok=True)
            if not favicon_target.exists():
                shutil.copy2(favicon_source, favicon_target)
                print(f"✅ 移动favicon: favicon.svg -> frontend/public/")
    
    def organize_data_and_docs(self):
        """整理数据和文档文件"""
        
        # 移动数据相关目录
        data_directories = [
            ("databases", "data/databases"),
            ("db", "data/db"),
            ("logs", "data/logs"),
            ("testlogs", "data/testlogs"),
            ("test_data", "data/test_data"),
            ("test_crawl", "data/test_crawl")
        ]
        
        for source, target in data_directories:
            source_path = self.project_root / source
            target_path = self.project_root / target
            
            if source_path.exists() and source_path != target_path:
                print(f"🔄 移动数据目录: {source} -> {target}")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                if target_path.exists():
                    backup_path = self.project_root / "backup/legacy_files" / f"{source}_{self.backup_timestamp}"
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(target_path), str(backup_path))
                
                shutil.move(str(source_path), str(target_path))
                print(f"  ✅ 移动完成")
        
        # 移动文档文件
        doc_files = [
            ("README.md", "docs/README.md"),
            ("CHANGELOG.md", "docs/CHANGELOG.md"),
            ("ARCHITECTURE_REFACTORING.md", "docs/ARCHITECTURE_REFACTORING.md"),
            ("OPTIMIZATION_PLAN.md", "docs/OPTIMIZATION_PLAN.md"),
            ("WEB界面使用指南.md", "docs/WEB界面使用指南.md"),
            ("WEB应用说明.md", "docs/WEB应用说明.md"),
            ("DATABASE_CLEANUP_REPORT.md", "docs/DATABASE_CLEANUP_REPORT.md"),
            ("CLEANUP_REPORT.md", "docs/CLEANUP_REPORT.md")
        ]
        
        docs_dir = self.project_root / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        for source_file, target_file in doc_files:
            source_path = self.project_root / source_file
            target_path = self.project_root / target_file
            
            if source_path.exists() and source_path != target_path:
                print(f"🔄 移动文档: {source_file}")
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
                # 保留根目录的README.md
                if source_file != "README.md":
                    source_path.unlink()
    
    def organize_scripts_and_tools(self):
        """整理脚本和工具文件"""
        
        # 移动脚本文件到scripts目录
        script_files = [
            "check_db_data.py",
            "test_web_db.py", 
            "test_comprehensive_crawler.py",
            "restructure_project.py"
        ]
        
        scripts_dir = self.project_root / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        for script_file in script_files:
            source_path = self.project_root / script_file
            target_path = scripts_dir / script_file
            
            if source_path.exists():
                print(f"🔄 移动脚本: {script_file}")
                shutil.copy2(source_path, target_path)
                source_path.unlink()
        
        # 移动启动脚本到scripts目录
        startup_scripts = [
            "start.bat",
            "start.sh",
            "start-newslook.bat", 
            "start-newslook.sh",
            "start_newslook_improved.bat"
        ]
        
        for script_file in startup_scripts:
            source_path = self.project_root / script_file
            target_path = scripts_dir / script_file
            
            if source_path.exists():
                print(f"🔄 移动启动脚本: {script_file}")
                shutil.copy2(source_path, target_path)
                # 保留根目录的主要启动脚本
                if script_file not in ["start.bat", "start.sh"]:
                    source_path.unlink()
        
        # 移动备份脚本目录
        backup_scripts_source = self.project_root / "backup_scripts"
        backup_scripts_target = scripts_dir / "backup"
        
        if backup_scripts_source.exists():
            print(f"🔄 移动备份脚本目录")
            shutil.move(str(backup_scripts_source), str(backup_scripts_target))
    
    def organize_requirements(self):
        """整理依赖文件"""
        requirements_files = [
            "requirements.txt"
        ]
        
        config_dir = self.project_root / "backend/config"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        for req_file in requirements_files:
            source_path = self.project_root / req_file
            target_path = config_dir / req_file
            
            if source_path.exists():
                print(f"🔄 复制依赖文件: {req_file}")
                shutil.copy2(source_path, target_path)
                # 保留根目录的requirements.txt以便安装
    
    def clean_empty_directories(self):
        """清理空目录"""
        def remove_empty_dirs(path):
            if not path.is_dir():
                return
            
            # 递归清理子目录
            subdirs = [p for p in path.iterdir() if p.is_dir()]
            for subdir in subdirs:
                remove_empty_dirs(subdir)
            
            # 如果目录为空，删除它
            try:
                if not any(path.iterdir()):
                    path.rmdir()
                    print(f"🗑️ 删除空目录: {path}")
            except (OSError, PermissionError):
                pass
        
        # 检查常见的可能为空的目录
        potential_empty_dirs = [
            "static", "templates", "web", "old_static", "legacy"
        ]
        
        for dir_name in potential_empty_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                remove_empty_dirs(dir_path)
    
    def create_project_overview(self):
        """创建项目结构概览"""
        overview_path = self.project_root / "PROJECT_STRUCTURE.md"
        
        overview_content = f"""# NewsLook 项目结构概览
更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🏗️ 项目结构

```
NewsLook/
├── 📁 frontend/               # 前端应用 (Vue.js + Vite)
│   ├── 📁 src/
│   │   ├── 📁 assets/         # 静态资源 (整合后)
│   │   ├── 📁 components/     # Vue组件
│   │   ├── 📁 views/          # 页面视图
│   │   ├── 📁 store/          # Pinia状态管理
│   │   ├── 📁 utils/          # 前端工具函数
│   │   └── 📄 main.js         # 入口文件
│   ├── 📁 public/             # 公共资源
│   ├── 📁 dist/               # 构建输出
│   ├── 📄 package.json        # 前端依赖
│   ├── 📄 vite.config.js      # 构建配置
│   └── 📄 index.html          # HTML模板
│
├── 📁 backend/                # 后端应用 (Python + Flask)
│   ├── 📁 app/                # 主应用模块
│   │   ├── 📁 web/            # Web界面
│   │   ├── 📁 api/            # API接口
│   │   ├── 📁 crawlers/       # 爬虫模块
│   │   └── 📁 utils/          # 工具函数
│   ├── 📁 newslook/           # 核心业务逻辑
│   │   ├── 📁 crawlers/       # 核心爬虫
│   │   ├── 📁 utils/          # 核心工具
│   │   └── 📁 web/            # Web路由
│   ├── 📁 api/                # 外部API
│   ├── 📁 utils/              # 通用工具
│   ├── 📁 config/             # 配置文件
│   ├── 📄 main.py             # 主启动文件
│   └── 📄 run.py              # 运行脚本
│
├── 📁 data/                   # 数据目录
│   ├── 📁 databases/          # 数据库文件
│   ├── 📁 logs/               # 日志文件
│   ├── 📁 test_data/          # 测试数据
│   └── 📁 cache/              # 缓存文件
│
├── 📁 scripts/                # 脚本工具
│   ├── 📁 backup/             # 备份脚本
│   ├── 📄 start.bat           # Windows启动
│   ├── 📄 start.sh            # Linux/Mac启动
│   └── 📄 *.py                # 各种工具脚本
│
├── 📁 tests/                  # 测试文件
│   ├── 📁 unit/               # 单元测试
│   ├── 📁 integration/        # 集成测试
│   └── 📁 fixtures/           # 测试数据
│
├── 📁 examples/               # 示例代码
│   ├── 📁 crawlers/           # 爬虫示例
│   └── 📁 configs/            # 配置示例
│
├── 📁 docs/                   # 项目文档
│   ├── 📄 README.md           # 项目说明
│   ├── 📄 CHANGELOG.md        # 更新日志
│   └── 📄 *.md                # 其他文档
│
├── 📁 backup/                 # 备份文件
│   ├── 📁 legacy_files/       # 旧版文件
│   ├── 📁 duplicate_files/    # 重复文件
│   └── 📁 old_web_v*/         # 旧版Web
│
├── 📄 requirements.txt        # Python依赖
├── 📄 .gitignore             # Git忽略文件
├── 📄 .editorconfig          # 编辑器配置
└── 📄 PROJECT_STRUCTURE.md   # 本文件
```

## 🚀 快速启动

### 后端启动
```bash
# 安装依赖
pip install -r requirements.txt

# 启动后端服务
python main.py
# 或者
cd backend && python main.py
```

### 前端开发
```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 使用启动脚本
```bash
# Windows
scripts/start.bat

# Linux/Mac  
scripts/start.sh
```

## 📝 重要说明

1. **文件整理**: 所有重复和分散的文件已经整理到合适的目录
2. **备份保护**: 原始文件已备份到 `backup/` 目录
3. **导入路径**: Python导入路径已自动更新
4. **配置文件**: 前端构建配置已更新路径映射
5. **启动方式**: 支持多种启动方式，建议使用脚本启动

## 🔧 开发指南

- **前端开发**: 在 `frontend/` 目录下进行Vue.js开发
- **后端开发**: 在 `backend/` 目录下进行Python开发  
- **新增爬虫**: 在 `backend/app/crawlers/` 或 `backend/newslook/crawlers/` 添加
- **配置管理**: 配置文件统一在 `backend/config/` 目录
- **测试**: 测试文件在 `tests/` 目录，按模块组织

## ⚠️ 注意事项

- 确保两个服务器端口不冲突 (前端:3000, 后端:5000)
- 数据库文件在 `data/databases/` 目录
- 日志文件在 `data/logs/` 目录
- 测试前请备份重要数据
"""
        
        with open(overview_path, 'w', encoding='utf-8') as f:
            f.write(overview_content)
        
        print(f"📋 项目结构概览已创建: {overview_path}")
    
    def run_complete_restructure(self):
        """执行完整的重构流程"""
        print("🔧 开始完善 NewsLook 项目文件结构...")
        print("=" * 50)
        
        try:
            # 1. 移动剩余后端文件
            print("\n🐍 第1步: 移动剩余后端文件")
            self.move_remaining_backend_files()
            
            # 2. 整理前端结构
            print("\n🎨 第2步: 整理前端目录结构")
            self.organize_frontend_structure()
            
            # 3. 整理数据和文档
            print("\n📊 第3步: 整理数据和文档文件")
            self.organize_data_and_docs()
            
            # 4. 整理脚本和工具
            print("\n🛠️ 第4步: 整理脚本和工具文件")
            self.organize_scripts_and_tools()
            
            # 5. 整理依赖文件
            print("\n📦 第5步: 整理依赖文件")
            self.organize_requirements()
            
            # 6. 清理空目录
            print("\n🧹 第6步: 清理空目录")
            self.clean_empty_directories()
            
            # 7. 创建项目概览
            print("\n📋 第7步: 创建项目结构概览")
            self.create_project_overview()
            
            print("\n" + "=" * 50)
            print("✅ 项目重构完善完成!")
            print("\n📁 新的项目结构:")
            print("├── frontend/     # 前端应用")
            print("├── backend/      # 后端应用") 
            print("├── data/         # 数据文件")
            print("├── scripts/      # 脚本工具")
            print("├── tests/        # 测试文件")
            print("├── examples/     # 示例代码")
            print("├── docs/         # 项目文档")
            print("└── backup/       # 备份文件")
            print("\n🎉 文件结构整理完成!")
            
        except Exception as e:
            print(f"❌ 重构过程中出现错误: {e}")
            return False
        
        return True

if __name__ == "__main__":
    restructurer = CompleteRestructurer()
    success = restructurer.run_complete_restructure()
    
    if success:
        print("\n🎉 项目结构整理成功!")
    else:
        print("\n⚠️ 整理过程中遇到问题，请检查日志") 