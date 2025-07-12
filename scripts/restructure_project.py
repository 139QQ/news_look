#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NewsLook 项目文件结构重构脚本
解决重复文件和分散资源问题
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime

class ProjectRestructurer:
    def __init__(self, project_root="."):
        self.project_root = Path(project_root)
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report = {
            "restructured_files": [],
            "consolidated_directories": [],
            "removed_duplicates": [],
            "created_directories": [],
            "updated_imports": []
        }
    
    def create_target_structure(self):
        """创建目标目录结构"""
        directories_to_create = [
            # 前端资源统一管理
            "frontend/src/assets",
            "frontend/src/components", 
            "frontend/src/views",
            "frontend/src/store",
            "frontend/src/utils",
            "frontend/public",
            "frontend/dist",
            
            # 后端资源整理
            "backend/app/web/static",
            "backend/app/web/templates", 
            "backend/app/api",
            "backend/app/crawlers",
            "backend/app/utils",
            "backend/config",
            
            # 统一备份目录
            "backup/web_resources",
            "backup/legacy_files",
            "backup/duplicate_files",
            
            # 文档和配置
            "docs/api",
            "docs/deployment", 
            "docs/development",
            
            # 数据和日志
            "data/databases",
            "data/logs",
            "data/cache",
            
            # 测试和示例
            "tests/unit",
            "tests/integration", 
            "tests/fixtures",
            "examples/crawlers",
            "examples/configs"
        ]
        
        for directory in directories_to_create:
            target_path = self.project_root / directory
            if not target_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)
                self.report["created_directories"].append(str(directory))
                print(f"✅ 创建目录: {directory}")
    
    def consolidate_static_resources(self):
        """整合分散的静态资源"""
        static_dirs = [
            "app/web/static",
            "newslook/web/static", 
            "src",
            "public"
        ]
        
        target_static_dir = self.project_root / "frontend/src/assets"
        
        for static_dir in static_dirs:
            source_path = self.project_root / static_dir
            if source_path.exists():
                print(f"🔄 整合静态资源: {static_dir} -> frontend/src/assets")
                
                # 移动文件到目标目录
                for item in source_path.rglob("*"):
                    if item.is_file() and not item.name.startswith('.'):
                        relative_path = item.relative_to(source_path)
                        target_file = target_static_dir / relative_path
                        
                        # 确保目标目录存在
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        # 处理重复文件
                        if target_file.exists():
                            backup_file = self.project_root / "backup/duplicate_files" / f"{item.name}_{self.backup_timestamp}"
                            shutil.copy2(item, backup_file)
                            self.report["removed_duplicates"].append({
                                "original": str(item),
                                "backup": str(backup_file)
                            })
                        else:
                            shutil.copy2(item, target_file)
                            self.report["restructured_files"].append({
                                "from": str(item),
                                "to": str(target_file)
                            })
    
    def consolidate_templates(self):
        """整合模板文件"""
        template_dirs = [
            "app/web/templates",
            "newslook/web/templates",
            "frontend/templates"
        ]
        
        target_template_dir = self.project_root / "backend/app/web/templates"
        
        for template_dir in template_dirs:
            source_path = self.project_root / template_dir
            if source_path.exists():
                print(f"🔄 整合模板文件: {template_dir} -> backend/app/web/templates")
                
                for item in source_path.rglob("*.html"):
                    relative_path = item.relative_to(source_path)
                    target_file = target_template_dir / relative_path
                    
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    if target_file.exists():
                        # 比较文件内容，如果不同则备份
                        with open(item, 'r', encoding='utf-8') as f1, open(target_file, 'r', encoding='utf-8') as f2:
                            if f1.read() != f2.read():
                                backup_file = self.project_root / "backup/duplicate_files" / f"{item.name}_{self.backup_timestamp}"
                                shutil.copy2(item, backup_file)
                                self.report["removed_duplicates"].append({
                                    "original": str(item),
                                    "backup": str(backup_file),
                                    "reason": "content_differs"
                                })
                    else:
                        shutil.copy2(item, target_file)
                        self.report["restructured_files"].append({
                            "from": str(item),
                            "to": str(target_file)
                        })
    
    def organize_backend_files(self):
        """整理后端文件"""
        # 移动主要的Python文件到backend目录
        backend_files = [
            ("app", "backend/app"),
            ("newslook", "backend/newslook"), 
            ("api", "backend/api"),
            ("utils", "backend/utils"),
            ("configs", "backend/config")
        ]
        
        for source, target in backend_files:
            source_path = self.project_root / source
            target_path = self.project_root / target
            
            if source_path.exists() and source != target.split('/')[-1]:
                print(f"🔄 移动后端文件: {source} -> {target}")
                
                if target_path.exists():
                    # 备份现有目录
                    backup_path = self.project_root / "backup/legacy_files" / f"{source}_{self.backup_timestamp}"
                    shutil.move(str(target_path), str(backup_path))
                
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source_path), str(target_path))
                
                self.report["restructured_files"].append({
                    "from": str(source_path),
                    "to": str(target_path)
                })
    
    def update_import_paths(self):
        """更新导入路径"""
        # 查找所有Python文件并更新导入路径
        python_files = list(self.project_root.rglob("*.py"))
        
        import_mappings = {
            "from backend.app.": "from backend.app.",
            "from backend.newslook.": "from backend.newslook.",
            "from backend.api.": "from backend.api.", 
            "from backend.utils.": "from backend.utils.",
            "import backend.app.": "import backend.app.",
            "import backend.newslook.": "import backend.newslook.",
            "import backend.api.": "import backend.api.",
            "import backend.utils.": "import backend.utils."
        }
        
        updated_files = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # 应用导入路径映射
                for old_import, new_import in import_mappings.items():
                    content = content.replace(old_import, new_import)
                
                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    updated_files.append(str(py_file))
                    
            except Exception as e:
                print(f"⚠️ 更新导入路径失败: {py_file} - {e}")
        
        self.report["updated_imports"] = updated_files
        print(f"✅ 更新了 {len(updated_files)} 个文件的导入路径")
    
    def create_frontend_config(self):
        """创建前端配置文件"""
        # 更新package.json路径配置
        package_json_path = self.project_root / "frontend/package.json"
        if package_json_path.exists():
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            # 更新脚本路径
            if "scripts" in package_data:
                package_data["scripts"]["dev"] = "vite"
                package_data["scripts"]["build"] = "vite build"
                package_data["scripts"]["preview"] = "vite preview"
            
            with open(package_json_path, 'w', encoding='utf-8') as f:
                json.dump(package_data, f, indent=2, ensure_ascii=False)
        
        # 创建vite配置
        vite_config_path = self.project_root / "frontend/vite.config.js"
        vite_config_content = '''import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@assets': resolve(__dirname, 'src/assets'),
      '@components': resolve(__dirname, 'src/components'),
      '@views': resolve(__dirname, 'src/views'),
      '@store': resolve(__dirname, 'src/store'),
      '@utils': resolve(__dirname, 'src/utils')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html')
      }
    }
  }
})'''
        
        with open(vite_config_path, 'w', encoding='utf-8') as f:
            f.write(vite_config_content)
    
    def clean_empty_directories(self):
        """清理空目录"""
        def remove_empty_dirs(path):
            if not path.is_dir():
                return
            
            # 递归清理子目录
            for subdir in path.iterdir():
                if subdir.is_dir():
                    remove_empty_dirs(subdir)
            
            # 如果目录为空，删除它
            try:
                if not any(path.iterdir()):
                    path.rmdir()
                    print(f"🗑️ 删除空目录: {path}")
            except OSError:
                pass
        
        # 清理常见的空目录位置
        for directory in ["src", "public", "static", "templates"]:
            dir_path = self.project_root / directory
            if dir_path.exists():
                remove_empty_dirs(dir_path)
    
    def generate_report(self):
        """生成重构报告"""
        report_path = self.project_root / f"RESTRUCTURE_REPORT_{self.backup_timestamp}.md"
        
        report_content = f"""# NewsLook 项目重构报告
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 重构概要
- 📁 创建目录: {len(self.report['created_directories'])} 个
- 📄 重组文件: {len(self.report['restructured_files'])} 个  
- 🔄 更新导入: {len(self.report['updated_imports'])} 个
- 🗑️ 移除重复: {len(self.report['removed_duplicates'])} 个

## 新的目录结构
```
NewsLook/
├── frontend/           # 前端资源统一管理
│   ├── src/
│   │   ├── assets/     # 静态资源 (原 static/)
│   │   ├── components/ # Vue组件
│   │   ├── views/      # 页面视图
│   │   ├── store/      # 状态管理
│   │   └── utils/      # 工具函数
│   ├── public/         # 公共资源
│   └── dist/           # 构建输出
├── backend/            # 后端资源整理
│   ├── app/            # 主应用 (原 app/)
│   ├── newslook/       # 核心模块 (原 newslook/)
│   ├── api/            # API接口 (原 api/)
│   ├── utils/          # 工具模块 (原 utils/)
│   └── config/         # 配置文件 (原 configs/)
├── backup/             # 统一备份
│   ├── web_resources/  # Web资源备份
│   ├── legacy_files/   # 旧版文件
│   └── duplicate_files/# 重复文件
├── docs/               # 文档整理
├── data/               # 数据目录
├── tests/              # 测试文件
└── examples/           # 示例代码
```

## 详细变更记录

### 创建的目录
"""
        
        for directory in self.report['created_directories']:
            report_content += f"- {directory}\n"
        
        report_content += "\n### 重组的文件\n"
        for file_info in self.report['restructured_files']:
            report_content += f"- `{file_info['from']}` → `{file_info['to']}`\n"
        
        report_content += "\n### 移除的重复文件\n"
        for dup_info in self.report['removed_duplicates']:
            report_content += f"- `{dup_info['original']}` (备份至 `{dup_info['backup']}`)\n"
        
        report_content += f"\n### 更新导入路径的文件\n"
        for file_path in self.report['updated_imports']:
            report_content += f"- {file_path}\n"
        
        report_content += """
## 后续步骤

1. **验证应用启动**
   ```bash
   # 后端
   cd backend
   python main.py
   
   # 前端  
   cd frontend
   npm run dev
   ```

2. **检查导入路径**
   - 确认所有Python导入路径正确
   - 检查前端组件引用路径

3. **清理工作**
   - 验证功能正常后可删除backup目录
   - 更新.gitignore文件

4. **文档更新**
   - 更新README.md中的目录结构说明
   - 更新部署文档中的路径配置

## 注意事项
- 所有原始文件已备份到backup目录
- 导入路径已自动更新，如有遗漏请手动修正
- 建议在删除备份文件前完整测试项目功能
"""
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"📋 重构报告已生成: {report_path}")
        return report_path
    
    def run_restructure(self):
        """执行完整的重构流程"""
        print("🚀 开始 NewsLook 项目文件结构重构...")
        print("=" * 50)
        
        try:
            # 1. 创建目标目录结构
            print("\n📁 第1步: 创建目标目录结构")
            self.create_target_structure()
            
            # 2. 整合静态资源
            print("\n🎨 第2步: 整合静态资源")
            self.consolidate_static_resources()
            
            # 3. 整合模板文件  
            print("\n📄 第3步: 整合模板文件")
            self.consolidate_templates()
            
            # 4. 整理后端文件
            print("\n🐍 第4步: 整理后端文件")
            self.organize_backend_files()
            
            # 5. 更新导入路径
            print("\n🔄 第5步: 更新导入路径")
            self.update_import_paths()
            
            # 6. 创建前端配置
            print("\n⚙️ 第6步: 创建前端配置")
            self.create_frontend_config()
            
            # 7. 清理空目录
            print("\n🧹 第7步: 清理空目录")  
            self.clean_empty_directories()
            
            # 8. 生成报告
            print("\n📋 第8步: 生成重构报告")
            report_path = self.generate_report()
            
            print("\n" + "=" * 50)
            print("✅ 项目重构完成!")
            print(f"📋 详细报告: {report_path}")
            print("\n建议下一步:")
            print("1. 检查应用能否正常启动")
            print("2. 验证所有功能正常") 
            print("3. 确认无误后可删除backup目录")
            
        except Exception as e:
            print(f"❌ 重构过程中出现错误: {e}")
            print("请检查错误信息并手动处理")
            return False
        
        return True

if __name__ == "__main__":
    restructurer = ProjectRestructurer()
    success = restructurer.run_restructure()
    
    if success:
        print("\n🎉 重构成功完成!")
    else:
        print("\n⚠️ 重构过程中遇到问题，请检查日志") 