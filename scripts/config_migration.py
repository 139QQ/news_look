#!/usr/bin/env python3
"""
NewsLook配置迁移脚本
将旧的.cfg/.ini配置文件迁移到新的YAML配置格式
"""

import os
import sys
import shutil
import yaml
import configparser
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConfigMigrator:
    """配置迁移管理器"""
    
    def __init__(self, project_root: str = None):
        """初始化配置迁移器"""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.configs_dir = self.project_root / "configs"
        self.backup_dir = self.project_root / "backup" / f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.target_config = self.configs_dir / "app.yaml"
        
        # 创建必要的目录
        self.configs_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 旧配置文件模式
        self.old_config_patterns = [
            "*.cfg", "*.ini", "*.conf"
        ]
        
        # 配置节映射
        self.section_mapping = {
            'database': 'database',
            'db': 'database',
            'sqlite': 'database',
            'web': 'web',
            'server': 'web',
            'flask': 'web',
            'crawler': 'crawler',
            'spider': 'crawler',
            'logging': 'logging',
            'log': 'logging',
            'monitor': 'monitoring',
            'monitoring': 'monitoring',
            'health': 'monitoring',
            'api': 'api',
            'cache': 'cache',
            'redis': 'cache'
        }
    
    def find_old_configs(self) -> List[Path]:
        """查找所有旧配置文件"""
        old_configs = []
        
        for pattern in self.old_config_patterns:
            # 在项目根目录搜索
            old_configs.extend(self.project_root.glob(pattern))
            # 在config目录搜索
            config_dir = self.project_root / "config"
            if config_dir.exists():
                old_configs.extend(config_dir.glob(pattern))
        
        # 过滤掉备份文件
        old_configs = [f for f in old_configs if 'backup' not in str(f)]
        
        logger.info(f"找到 {len(old_configs)} 个旧配置文件: {[str(f) for f in old_configs]}")
        return old_configs
    
    def parse_old_config(self, config_path: Path) -> Dict[str, Any]:
        """解析旧配置文件"""
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        
        parsed_config = {}
        
        for section_name in config.sections():
            # 映射到新的节名
            mapped_section = self.section_mapping.get(section_name.lower(), section_name)
            
            if mapped_section not in parsed_config:
                parsed_config[mapped_section] = {}
            
            for key, value in config.items(section_name):
                # 类型转换
                converted_value = self._convert_value(value)
                parsed_config[mapped_section][key] = converted_value
        
        logger.info(f"解析配置文件 {config_path}: {len(parsed_config)} 个节")
        return parsed_config
    
    def _convert_value(self, value: str) -> Any:
        """转换配置值类型"""
        if not value:
            return None
        
        # 布尔值转换
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        elif value.lower() in ('false', 'no', 'off', '0'):
            return False
        
        # 数字转换
        try:
            # 尝试转换为整数
            if '.' not in value:
                return int(value)
            # 尝试转换为浮点数
            return float(value)
        except ValueError:
            pass
        
        # 列表转换（逗号分隔）
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        # 返回字符串
        return value
    
    def merge_configs(self, config_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并多个配置字典"""
        merged_config = {}
        
        for config in config_list:
            for section, settings in config.items():
                if section not in merged_config:
                    merged_config[section] = {}
                
                merged_config[section].update(settings)
        
        return merged_config
    
    def create_new_config(self, merged_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的YAML配置结构"""
        new_config = {
            'app': {
                'name': 'NewsLook',
                'version': '2.0.0',
                'description': '财经新闻爬虫系统',
                'environment': 'production'
            },
            'database': {
                'type': 'sqlite',
                'path': 'data/',
                'connection_pool': {
                    'max_connections': 20,
                    'min_connections': 5,
                    'timeout': 30
                },
                'health_check': {
                    'enabled': True,
                    'interval': 60,
                    'timeout': 10
                }
            },
            'web': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': False,
                'threaded': True,
                'cors': {
                    'enabled': True,
                    'origins': ['*']
                }
            },
            'crawler': {
                'concurrent_limit': 10,
                'request_delay': 1,
                'retry_attempts': 3,
                'timeout': 30,
                'user_agents': [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                ]
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'logs/app.log',
                'rotation': {
                    'max_size': '10MB',
                    'backup_count': 5
                }
            },
            'monitoring': {
                'enabled': True,
                'metrics': {
                    'enabled': True,
                    'port': 9090
                },
                'health_check': {
                    'enabled': True,
                    'endpoint': '/health'
                }
            },
            'api': {
                'version': 'v1',
                'rate_limit': {
                    'enabled': True,
                    'requests_per_minute': 100
                },
                'response_format': {
                    'standard': True,
                    'include_metadata': True
                }
            },
            'cache': {
                'type': 'memory',
                'ttl': 3600,
                'max_size': 1000
            }
        }
        
        # 合并旧配置
        for section, settings in merged_config.items():
            if section in new_config:
                new_config[section].update(settings)
            else:
                new_config[section] = settings
        
        return new_config
    
    def backup_old_configs(self, old_configs: List[Path]):
        """备份旧配置文件"""
        for config_path in old_configs:
            backup_path = self.backup_dir / config_path.name
            shutil.copy2(config_path, backup_path)
            logger.info(f"备份配置文件: {config_path} -> {backup_path}")
    
    def save_new_config(self, config: Dict[str, Any]):
        """保存新配置文件"""
        with open(self.target_config, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        logger.info(f"新配置文件已保存: {self.target_config}")
    
    def cleanup_old_configs(self, old_configs: List[Path]):
        """清理旧配置文件"""
        for config_path in old_configs:
            try:
                config_path.unlink()
                logger.info(f"删除旧配置文件: {config_path}")
            except Exception as e:
                logger.warning(f"删除配置文件失败 {config_path}: {e}")
    
    def validate_new_config(self) -> bool:
        """验证新配置文件"""
        try:
            with open(self.target_config, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 检查必要的配置节
            required_sections = ['app', 'database', 'web', 'crawler', 'logging']
            for section in required_sections:
                if section not in config:
                    logger.error(f"缺少必要的配置节: {section}")
                    return False
            
            logger.info("新配置文件验证通过")
            return True
        except Exception as e:
            logger.error(f"配置文件验证失败: {e}")
            return False
    
    def migrate(self, cleanup: bool = True) -> bool:
        """执行配置迁移"""
        try:
            logger.info("开始配置迁移...")
            
            # 1. 查找旧配置文件
            old_configs = self.find_old_configs()
            
            if not old_configs:
                logger.info("没有找到旧配置文件，创建默认配置")
                default_config = self.create_new_config({})
                self.save_new_config(default_config)
                return True
            
            # 2. 备份旧配置
            self.backup_old_configs(old_configs)
            
            # 3. 解析旧配置
            parsed_configs = []
            for config_path in old_configs:
                try:
                    parsed_config = self.parse_old_config(config_path)
                    parsed_configs.append(parsed_config)
                except Exception as e:
                    logger.warning(f"解析配置文件失败 {config_path}: {e}")
            
            # 4. 合并配置
            merged_config = self.merge_configs(parsed_configs)
            
            # 5. 创建新配置
            new_config = self.create_new_config(merged_config)
            
            # 6. 保存新配置
            self.save_new_config(new_config)
            
            # 7. 验证新配置
            if not self.validate_new_config():
                logger.error("配置验证失败，迁移终止")
                return False
            
            # 8. 清理旧配置（可选）
            if cleanup:
                self.cleanup_old_configs(old_configs)
            
            logger.info("配置迁移完成")
            return True
            
        except Exception as e:
            logger.error(f"配置迁移失败: {e}")
            return False
    
    def generate_migration_report(self) -> str:
        """生成迁移报告"""
        report = f"""
# NewsLook配置迁移报告

## 迁移时间
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 迁移路径
- 源配置目录: {self.project_root}
- 目标配置文件: {self.target_config}
- 备份目录: {self.backup_dir}

## 迁移状态
- 状态: {'成功' if self.target_config.exists() else '失败'}
- 配置文件大小: {self.target_config.stat().st_size if self.target_config.exists() else 0} bytes

## 配置结构
"""
        
        if self.target_config.exists():
            try:
                with open(self.target_config, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                for section in config.keys():
                    report += f"- {section}\n"
            except Exception as e:
                report += f"- 读取配置文件失败: {e}\n"
        
        return report

def main():
    """主函数"""
    print("NewsLook配置迁移工具")
    print("=" * 50)
    
    # 创建迁移器
    migrator = ConfigMigrator()
    
    # 执行迁移
    success = migrator.migrate(cleanup=True)
    
    if success:
        print("\n✅ 配置迁移成功完成!")
        print(f"新配置文件: {migrator.target_config}")
        print(f"备份目录: {migrator.backup_dir}")
        
        # 生成报告
        report = migrator.generate_migration_report()
        report_path = migrator.project_root / "CONFIG_MIGRATION_REPORT.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"迁移报告: {report_path}")
    else:
        print("\n❌ 配置迁移失败!")
        sys.exit(1)

if __name__ == "__main__":
    main() 