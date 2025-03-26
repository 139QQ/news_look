#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文档生成工具

此脚本用于从代码注释生成项目文档，支持生成HTML或Markdown格式文档。
它会自动解析Python源码中的docstrings并生成结构化的API文档。

用法：
python scripts/utils/documentation_generator.py [-h] [--output OUTPUT] 
                                              [--format {html,markdown}]
                                              [--title TITLE]
                                              [--source SOURCE]
"""

import os
import sys
import re
import ast
import argparse
import logging
import inspect
import importlib
import pkgutil
import glob
import json
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("documentation_generator")

class DocstringParser:
    """解析Python文件中的文档字符串"""
    
    @staticmethod
    def parse_module_docstring(source_code):
        """解析模块级别的文档字符串"""
        try:
            module = ast.parse(source_code)
            docstring = ast.get_docstring(module)
            return docstring
        except SyntaxError:
            logger.error("解析模块文档字符串时出现语法错误")
            return None
    
    @staticmethod
    def parse_class_docstring(source_code, class_name=None):
        """解析类级别的文档字符串"""
        try:
            module = ast.parse(source_code)
            classes = {}
            
            for node in module.body:
                if isinstance(node, ast.ClassDef):
                    if class_name is None or node.name == class_name:
                        classes[node.name] = {
                            'docstring': ast.get_docstring(node),
                            'methods': {}
                        }
                        
                        # 解析方法
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                classes[node.name]['methods'][item.name] = {
                                    'docstring': ast.get_docstring(item),
                                    'args': [arg.arg for arg in item.args.args if arg.arg != 'self'],
                                    'decorators': [d.id for d in item.decorator_list if isinstance(d, ast.Name)]
                                }
            
            return classes
        except SyntaxError:
            logger.error("解析类文档字符串时出现语法错误")
            return {}
    
    @staticmethod
    def parse_function_docstring(source_code, function_name=None):
        """解析函数级别的文档字符串"""
        try:
            module = ast.parse(source_code)
            functions = {}
            
            for node in module.body:
                if isinstance(node, ast.FunctionDef):
                    if function_name is None or node.name == function_name:
                        functions[node.name] = {
                            'docstring': ast.get_docstring(node),
                            'args': [arg.arg for arg in node.args.args],
                            'decorators': [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                        }
            
            return functions
        except SyntaxError:
            logger.error("解析函数文档字符串时出现语法错误")
            return {}
    
    @staticmethod
    def parse_file(file_path):
        """解析整个Python文件中的文档字符串"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            result = {
                'module': {
                    'name': os.path.basename(file_path).replace('.py', ''),
                    'path': file_path,
                    'docstring': DocstringParser.parse_module_docstring(source_code)
                },
                'classes': DocstringParser.parse_class_docstring(source_code),
                'functions': DocstringParser.parse_function_docstring(source_code)
            }
            
            return result
        except Exception as e:
            logger.error(f"解析文件 {file_path} 时出错: {str(e)}")
            return None

class ModuleCollector:
    """收集项目中的Python模块"""
    
    @staticmethod
    def collect_modules(directory):
        """收集指定目录中的所有Python模块"""
        modules = []
        
        if not os.path.exists(directory):
            logger.error(f"目录不存在: {directory}")
            return modules
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py') and not file.startswith('_'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, os.path.dirname(directory))
                    module_path = rel_path.replace(os.path.sep, '.').replace('.py', '')
                    
                    modules.append({
                        'name': file.replace('.py', ''),
                        'path': file_path,
                        'module_path': module_path
                    })
        
        return modules
    
    @staticmethod
    def collect_packages(directory):
        """收集指定目录中的所有Python包"""
        packages = []
        
        if not os.path.exists(directory):
            logger.error(f"目录不存在: {directory}")
            return packages
        
        for root, dirs, files in os.walk(directory):
            if '__init__.py' in files:
                package_path = os.path.relpath(root, os.path.dirname(directory))
                package_name = package_path.replace(os.path.sep, '.')
                
                packages.append({
                    'name': os.path.basename(root),
                    'path': root,
                    'package_path': package_name
                })
        
        return packages

class DocumentationGenerator:
    """生成文档的主类"""
    
    def __init__(self, source_directory, output_directory, format='html', title='API文档'):
        self.source_directory = source_directory
        self.output_directory = output_directory
        self.format = format
        self.title = title
        self.parser = DocstringParser()
        self.collector = ModuleCollector()
        
        # 确保输出目录存在
        os.makedirs(self.output_directory, exist_ok=True)
    
    def generate(self):
        """生成文档"""
        logger.info(f"开始生成{self.format}格式的文档...")
        
        # 收集模块和包
        modules = self.collector.collect_modules(self.source_directory)
        packages = self.collector.collect_packages(self.source_directory)
        
        logger.info(f"找到 {len(modules)} 个模块和 {len(packages)} 个包")
        
        # 解析所有模块的文档字符串
        parsed_modules = []
        for module in modules:
            parsed = self.parser.parse_file(module['path'])
            if parsed:
                parsed_modules.append(parsed)
        
        # 生成文档
        if self.format == 'html':
            self._generate_html(parsed_modules, packages)
        else:  # markdown
            self._generate_markdown(parsed_modules, packages)
        
        logger.info(f"文档生成完成, 保存在 {self.output_directory}")
    
    def _generate_html(self, parsed_modules, packages):
        """生成HTML格式的文档"""
        # 生成索引页
        index_path = os.path.join(self.output_directory, 'index.html')
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_html_index(parsed_modules, packages))
        
        # 为每个模块生成单独的页面
        for module in parsed_modules:
            module_name = module['module']['name']
            module_path = os.path.join(self.output_directory, f"{module_name}.html")
            
            with open(module_path, 'w', encoding='utf-8') as f:
                f.write(self._generate_html_module(module))
        
        # 复制CSS文件
        css_path = os.path.join(self.output_directory, 'style.css')
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(self._get_css())
    
    def _generate_html_index(self, parsed_modules, packages):
        """生成HTML索引页"""
        html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>{self.title}</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <div class="content">
            <div class="sidebar">
                <h2>目录</h2>
                <ul class="toc">
                    <li><a href="#packages">包</a></li>
                    <li><a href="#modules">模块</a></li>
                </ul>
            </div>
            
            <div class="main">
                <section id="packages">
                    <h2>包</h2>
                    <ul class="package-list">
        """
        
        # 添加包列表
        for package in packages:
            html += f'<li><strong>{package["name"]}</strong> <small>({package["package_path"]})</small></li>\n'
        
        html += """
                    </ul>
                </section>
                
                <section id="modules">
                    <h2>模块</h2>
                    <ul class="module-list">
        """
        
        # 添加模块列表
        for module in parsed_modules:
            module_name = module['module']['name']
            docstring_summary = ""
            if module['module']['docstring']:
                docstring_lines = module['module']['docstring'].split('\n')
                if docstring_lines:
                    docstring_summary = docstring_lines[0]
            
            html += f'<li><a href="{module_name}.html">{module_name}</a> - {docstring_summary}</li>\n'
        
        html += """
                    </ul>
                </section>
            </div>
        </div>
        
        <footer>
            <p>由文档生成工具自动生成</p>
        </footer>
    </div>
</body>
</html>
        """
        
        return html
    
    def _generate_html_module(self, module):
        """生成模块HTML页面"""
        module_name = module['module']['name']
        docstring = module['module']['docstring'] or "无文档"
        
        html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{module_name} - {self.title}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>{module_name}</h1>
            <p><a href="index.html">返回索引</a></p>
        </header>
        
        <div class="content">
            <div class="sidebar">
                <h2>目录</h2>
                <ul class="toc">
                    <li><a href="#module">模块</a></li>
        """
        
        if module['classes']:
            html += '<li><a href="#classes">类</a></li>\n'
        
        if module['functions']:
            html += '<li><a href="#functions">函数</a></li>\n'
        
        html += """
                </ul>
            </div>
            
            <div class="main">
                <section id="module">
                    <h2>模块文档</h2>
                    <div class="docstring">
        """
        
        # 添加模块文档
        html += f'<pre>{docstring}</pre>'
        
        # 添加类文档
        if module['classes']:
            html += """
                    </div>
                </section>
                
                <section id="classes">
                    <h2>类</h2>
            """
            
            for class_name, class_info in module['classes'].items():
                class_docstring = class_info['docstring'] or "无文档"
                
                html += f"""
                    <div class="class-item">
                        <h3>{class_name}</h3>
                        <div class="docstring">
                            <pre>{class_docstring}</pre>
                        </div>
                """
                
                if class_info['methods']:
                    html += '<h4>方法</h4>\n<ul class="method-list">\n'
                    
                    for method_name, method_info in class_info['methods'].items():
                        method_docstring = method_info['docstring'] or "无文档"
                        method_args = ", ".join(method_info['args'])
                        
                        html += f"""
                        <li>
                            <div class="method-signature">{method_name}({method_args})</div>
                            <div class="docstring">
                                <pre>{method_docstring}</pre>
                            </div>
                        </li>
                        """
                    
                    html += '</ul>\n'
                
                html += '</div>\n'
        
        # 添加函数文档
        if module['functions']:
            html += """
                    </div>
                </section>
                
                <section id="functions">
                    <h2>函数</h2>
            """
            
            for func_name, func_info in module['functions'].items():
                func_docstring = func_info['docstring'] or "无文档"
                func_args = ", ".join(func_info['args'])
                
                html += f"""
                    <div class="function-item">
                        <h3>{func_name}({func_args})</h3>
                        <div class="docstring">
                            <pre>{func_docstring}</pre>
                        </div>
                    </div>
                """
        
        html += """
                    </div>
                </section>
            </div>
        </div>
        
        <footer>
            <p>由文档生成工具自动生成</p>
        </footer>
    </div>
</body>
</html>
        """
        
        return html
    
    def _generate_markdown(self, parsed_modules, packages):
        """生成Markdown格式的文档"""
        # 生成索引页
        index_path = os.path.join(self.output_directory, 'README.md')
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_markdown_index(parsed_modules, packages))
        
        # 为每个模块生成单独的页面
        for module in parsed_modules:
            module_name = module['module']['name']
            module_path = os.path.join(self.output_directory, f"{module_name}.md")
            
            with open(module_path, 'w', encoding='utf-8') as f:
                f.write(self._generate_markdown_module(module))
    
    def _generate_markdown_index(self, parsed_modules, packages):
        """生成Markdown索引页"""
        md = f"# {self.title}\n\n"
        md += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # 添加目录
        md += "## 目录\n\n"
        md += "- [包](#包)\n"
        md += "- [模块](#模块)\n\n"
        
        # 添加包列表
        md += "## 包\n\n"
        for package in packages:
            md += f"- **{package['name']}** ({package['package_path']})\n"
        
        md += "\n## 模块\n\n"
        
        # 添加模块列表
        for module in parsed_modules:
            module_name = module['module']['name']
            docstring_summary = ""
            if module['module']['docstring']:
                docstring_lines = module['module']['docstring'].split('\n')
                if docstring_lines:
                    docstring_summary = docstring_lines[0]
            
            md += f"- [{module_name}]({module_name}.md) - {docstring_summary}\n"
        
        return md
    
    def _generate_markdown_module(self, module):
        """生成模块Markdown页面"""
        module_name = module['module']['name']
        docstring = module['module']['docstring'] or "无文档"
        
        md = f"# {module_name}\n\n"
        md += f"[返回索引](README.md)\n\n"
        
        # 添加目录
        md += "## 目录\n\n"
        md += "- [模块描述](#模块描述)\n"
        
        if module['classes']:
            md += "- [类](#类)\n"
        
        if module['functions']:
            md += "- [函数](#函数)\n"
        
        md += "\n## 模块描述\n\n"
        md += f"```\n{docstring}\n```\n\n"
        
        # 添加类文档
        if module['classes']:
            md += "## 类\n\n"
            
            for class_name, class_info in module['classes'].items():
                class_docstring = class_info['docstring'] or "无文档"
                
                md += f"### {class_name}\n\n"
                md += f"```\n{class_docstring}\n```\n\n"
                
                if class_info['methods']:
                    md += "#### 方法\n\n"
                    
                    for method_name, method_info in class_info['methods'].items():
                        method_docstring = method_info['docstring'] or "无文档"
                        method_args = ", ".join(method_info['args'])
                        
                        md += f"- **{method_name}({method_args})**\n\n"
                        md += f"```\n{method_docstring}\n```\n\n"
        
        # 添加函数文档
        if module['functions']:
            md += "## 函数\n\n"
            
            for func_name, func_info in module['functions'].items():
                func_docstring = func_info['docstring'] or "无文档"
                func_args = ", ".join(func_info['args'])
                
                md += f"### {func_name}({func_args})\n\n"
                md += f"```\n{func_docstring}\n```\n\n"
        
        return md
    
    def _get_css(self):
        """获取CSS样式"""
        return """
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f8f9fa;
            }
            
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            
            header {
                background-color: #343a40;
                color: white;
                padding: 20px;
                margin-bottom: 20px;
                border-radius: 5px;
            }
            
            header h1 {
                margin-bottom: 10px;
            }
            
            header a {
                color: #17a2b8;
                text-decoration: none;
            }
            
            header a:hover {
                text-decoration: underline;
            }
            
            .content {
                display: flex;
                background-color: white;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }
            
            .sidebar {
                width: 25%;
                padding: 20px;
                background-color: #f1f3f5;
                border-right: 1px solid #dee2e6;
            }
            
            .main {
                width: 75%;
                padding: 20px;
            }
            
            h2 {
                margin: 20px 0;
                padding-bottom: 10px;
                border-bottom: 1px solid #dee2e6;
                color: #343a40;
            }
            
            h3 {
                margin: 15px 0;
                color: #495057;
            }
            
            h4 {
                margin: 10px 0;
                color: #6c757d;
            }
            
            ul {
                list-style-position: inside;
                margin-bottom: 20px;
            }
            
            li {
                margin-bottom: 5px;
            }
            
            .toc {
                list-style-type: none;
            }
            
            .toc a {
                text-decoration: none;
                color: #007bff;
            }
            
            .toc a:hover {
                text-decoration: underline;
            }
            
            .docstring {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 15px;
                border-left: 3px solid #17a2b8;
                overflow-x: auto;
            }
            
            pre {
                white-space: pre-wrap;
                font-family: Consolas, Monaco, "Andale Mono", monospace;
                font-size: 14px;
            }
            
            .class-item, .function-item {
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 1px solid #eee;
            }
            
            .method-list {
                list-style-type: none;
                margin-left: 20px;
            }
            
            .method-signature {
                font-family: Consolas, Monaco, "Andale Mono", monospace;
                color: #343a40;
                margin-bottom: 5px;
                font-weight: bold;
            }
            
            footer {
                margin-top: 20px;
                padding: 20px;
                text-align: center;
                color: #6c757d;
                font-size: 14px;
            }
        """

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="文档生成工具")
    parser.add_argument("--output", default="docs", help="输出目录")
    parser.add_argument("--format", choices=["html", "markdown"], default="html", help="文档格式")
    parser.add_argument("--title", default="API文档", help="文档标题")
    parser.add_argument("--source", default="newslook", help="源代码目录")
    
    args = parser.parse_args()
    
    # 检查源目录是否存在
    if not os.path.exists(args.source):
        logger.error(f"源目录不存在: {args.source}")
        return
    
    # 生成文档
    generator = DocumentationGenerator(
        source_directory=args.source,
        output_directory=args.output,
        format=args.format,
        title=args.title
    )
    
    generator.generate()

if __name__ == "__main__":
    main()