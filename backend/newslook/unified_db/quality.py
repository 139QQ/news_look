#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsLook 数据质量引擎模块
提供数据质量规则定义、检查和监控功能
"""

import re
import json
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import logging
from sqlalchemy.orm import Session
from .models import QualityRule as QualityRuleModel, QualityCheckResult

logger = logging.getLogger(__name__)


class QualityRuleType(Enum):
    """数据质量规则类型"""
    NOT_NULL = "not_null"
    UNIQUE = "unique"
    RANGE = "range"
    PATTERN = "pattern"
    REFERENCE = "reference"
    CUSTOM = "custom"
    LENGTH = "length"
    FORMAT = "format"
    ENUM = "enum"


class QualityRule:
    """数据质量规则"""
    
    def __init__(self, rule_id: str, rule_type: QualityRuleType, 
                 target_table: str, target_field: str, 
                 config: Dict[str, Any], severity: str = "ERROR"):
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.target_table = target_table
        self.target_field = target_field
        self.config = config
        self.severity = severity
    
    def validate(self, data: Dict[str, Any], db_session: Optional[Session] = None) -> Dict[str, Any]:
        """
        验证数据是否符合质量规则
        
        Args:
            data: 待验证的数据
            db_session: 数据库会话(用于UNIQUE等需要查询数据库的规则)
            
        Returns:
            验证结果字典
        """
        result = {
            'rule_id': self.rule_id,
            'rule_type': self.rule_type.value,
            'target_field': self.target_field,
            'passed': True,
            'errors': [],
            'warnings': []
        }
        
        field_value = data.get(self.target_field)
        
        try:
            if self.rule_type == QualityRuleType.NOT_NULL:
                self._validate_not_null(field_value, result)
            
            elif self.rule_type == QualityRuleType.UNIQUE:
                self._validate_unique(field_value, result, db_session)
            
            elif self.rule_type == QualityRuleType.RANGE:
                self._validate_range(field_value, result)
            
            elif self.rule_type == QualityRuleType.PATTERN:
                self._validate_pattern(field_value, result)
            
            elif self.rule_type == QualityRuleType.LENGTH:
                self._validate_length(field_value, result)
            
            elif self.rule_type == QualityRuleType.FORMAT:
                self._validate_format(field_value, result)
            
            elif self.rule_type == QualityRuleType.ENUM:
                self._validate_enum(field_value, result)
            
            elif self.rule_type == QualityRuleType.REFERENCE:
                self._validate_reference(field_value, result, db_session)
            
            elif self.rule_type == QualityRuleType.CUSTOM:
                self._validate_custom(field_value, data, result)
                
        except Exception as e:
            result['passed'] = False
            result['errors'].append(f"规则验证异常: {str(e)}")
            logger.error(f"质量规则 {self.rule_id} 验证异常: {e}")
        
        return result
    
    def _validate_not_null(self, value: Any, result: Dict[str, Any]):
        """验证非空"""
        if value is None or (isinstance(value, str) and value.strip() == ''):
            result['passed'] = False
            result['errors'].append(f'字段 {self.target_field} 不能为空')
    
    def _validate_unique(self, value: Any, result: Dict[str, Any], db_session: Optional[Session]):
        """验证唯一性"""
        if not db_session:
            result['warnings'].append('无法验证唯一性：缺少数据库会话')
            return
        
        if value is None:
            return
        
        # 这里需要根据实际的表结构进行查询
        # 示例实现，实际需要动态构建查询
        try:
            from sqlalchemy import text
            query = text(f"SELECT COUNT(*) FROM {self.target_table} WHERE {self.target_field} = :value")
            count = db_session.execute(query, {'value': value}).scalar()
            
            if count > 0:
                result['passed'] = False
                result['errors'].append(f'字段 {self.target_field} 值 {value} 已存在，违反唯一性约束')
        except Exception as e:
            result['warnings'].append(f'唯一性验证失败: {str(e)}')
    
    def _validate_range(self, value: Any, result: Dict[str, Any]):
        """验证范围"""
        if value is None:
            return
        
        min_val = self.config.get('min')
        max_val = self.config.get('max')
        
        try:
            numeric_value = float(value)
            
            if min_val is not None and numeric_value < min_val:
                result['passed'] = False
                result['errors'].append(f'字段 {self.target_field} 值 {value} 小于最小值 {min_val}')
            
            if max_val is not None and numeric_value > max_val:
                result['passed'] = False
                result['errors'].append(f'字段 {self.target_field} 值 {value} 大于最大值 {max_val}')
                
        except (ValueError, TypeError):
            result['passed'] = False
            result['errors'].append(f'字段 {self.target_field} 值 {value} 不是有效数字')
    
    def _validate_pattern(self, value: Any, result: Dict[str, Any]):
        """验证正则模式"""
        if value is None:
            return
        
        pattern = self.config.get('pattern')
        if not pattern:
            result['warnings'].append('模式验证规则缺少pattern配置')
            return
        
        try:
            if not re.match(pattern, str(value)):
                result['passed'] = False
                result['errors'].append(f'字段 {self.target_field} 值 {value} 不匹配模式 {pattern}')
        except re.error as e:
            result['passed'] = False
            result['errors'].append(f'正则表达式错误: {str(e)}')
    
    def _validate_length(self, value: Any, result: Dict[str, Any]):
        """验证长度"""
        if value is None:
            return
        
        min_length = self.config.get('min_length')
        max_length = self.config.get('max_length')
        
        value_length = len(str(value))
        
        if min_length is not None and value_length < min_length:
            result['passed'] = False
            result['errors'].append(f'字段 {self.target_field} 长度 {value_length} 小于最小长度 {min_length}')
        
        if max_length is not None and value_length > max_length:
            result['passed'] = False
            result['errors'].append(f'字段 {self.target_field} 长度 {value_length} 大于最大长度 {max_length}')
    
    def _validate_format(self, value: Any, result: Dict[str, Any]):
        """验证格式（如日期、邮箱、URL等）"""
        if value is None:
            return
        
        format_type = self.config.get('format_type')
        
        if format_type == 'email':
            self._validate_email_format(value, result)
        elif format_type == 'url':
            self._validate_url_format(value, result)
        elif format_type == 'date':
            self._validate_date_format(value, result)
        elif format_type == 'datetime':
            self._validate_datetime_format(value, result)
        else:
            result['warnings'].append(f'未知的格式类型: {format_type}')
    
    def _validate_email_format(self, value: Any, result: Dict[str, Any]):
        """验证邮箱格式"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, str(value)):
            result['passed'] = False
            result['errors'].append(f'字段 {self.target_field} 值 {value} 不是有效的邮箱格式')
    
    def _validate_url_format(self, value: Any, result: Dict[str, Any]):
        """验证URL格式"""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(str(value))
            if not all([parsed.scheme, parsed.netloc]):
                result['passed'] = False
                result['errors'].append(f'字段 {self.target_field} 值 {value} 不是有效的URL格式')
        except Exception:
            result['passed'] = False
            result['errors'].append(f'字段 {self.target_field} 值 {value} URL格式验证失败')
    
    def _validate_date_format(self, value: Any, result: Dict[str, Any]):
        """验证日期格式"""
        date_format = self.config.get('date_format', '%Y-%m-%d')
        try:
            datetime.strptime(str(value), date_format)
        except ValueError:
            result['passed'] = False
            result['errors'].append(f'字段 {self.target_field} 值 {value} 不匹配日期格式 {date_format}')
    
    def _validate_datetime_format(self, value: Any, result: Dict[str, Any]):
        """验证日期时间格式"""
        datetime_format = self.config.get('datetime_format', '%Y-%m-%d %H:%M:%S')
        try:
            datetime.strptime(str(value), datetime_format)
        except ValueError:
            result['passed'] = False
            result['errors'].append(f'字段 {self.target_field} 值 {value} 不匹配日期时间格式 {datetime_format}')
    
    def _validate_enum(self, value: Any, result: Dict[str, Any]):
        """验证枚举值"""
        allowed_values = self.config.get('allowed_values', [])
        
        if value not in allowed_values:
            result['passed'] = False
            result['errors'].append(f'字段 {self.target_field} 值 {value} 不在允许的值列表中: {allowed_values}')
    
    def _validate_reference(self, value: Any, result: Dict[str, Any], db_session: Optional[Session]):
        """验证外键引用"""
        if not db_session:
            result['warnings'].append('无法验证引用完整性：缺少数据库会话')
            return
        
        if value is None:
            return
        
        ref_table = self.config.get('ref_table')
        ref_field = self.config.get('ref_field')
        
        if not ref_table or not ref_field:
            result['warnings'].append('引用验证规则缺少ref_table或ref_field配置')
            return
        
        try:
            from sqlalchemy import text
            query = text(f"SELECT COUNT(*) FROM {ref_table} WHERE {ref_field} = :value")
            count = db_session.execute(query, {'value': value}).scalar()
            
            if count == 0:
                result['passed'] = False
                result['errors'].append(f'字段 {self.target_field} 引用的值 {value} 在表 {ref_table} 中不存在')
        except Exception as e:
            result['warnings'].append(f'引用验证失败: {str(e)}')
    
    def _validate_custom(self, value: Any, data: Dict[str, Any], result: Dict[str, Any]):
        """自定义验证"""
        custom_function = self.config.get('custom_function')
        
        if not custom_function:
            result['warnings'].append('自定义验证规则缺少custom_function配置')
            return
        
        try:
            # 这里可以实现自定义函数的调用
            # 为了安全考虑，实际项目中应该限制可执行的函数
            if callable(custom_function):
                is_valid = custom_function(value, data)
                if not is_valid:
                    result['passed'] = False
                    result['errors'].append(f'字段 {self.target_field} 未通过自定义验证')
            else:
                result['warnings'].append('自定义验证函数不是可调用对象')
        except Exception as e:
            result['passed'] = False
            result['errors'].append(f'自定义验证异常: {str(e)}')


class QualityEngine:
    """数据质量引擎"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db_session = db_session
        self.rules: List[QualityRule] = []
        self.rule_cache: Dict[str, QualityRule] = {}
    
    def add_rule(self, rule: QualityRule):
        """添加质量规则"""
        self.rules.append(rule)
        self.rule_cache[rule.rule_id] = rule
        logger.info(f"添加质量规则: {rule.rule_id} ({rule.rule_type.value})")
    
    def remove_rule(self, rule_id: str):
        """移除质量规则"""
        if rule_id in self.rule_cache:
            rule = self.rule_cache[rule_id]
            self.rules.remove(rule)
            del self.rule_cache[rule_id]
            logger.info(f"移除质量规则: {rule_id}")
    
    def get_rule(self, rule_id: str) -> Optional[QualityRule]:
        """获取质量规则"""
        return self.rule_cache.get(rule_id)
    
    def load_rules_from_db(self):
        """从数据库加载质量规则"""
        if not self.db_session:
            logger.warning("无法从数据库加载规则：缺少数据库会话")
            return
        
        try:
            db_rules = self.db_session.query(QualityRuleModel).filter(
                QualityRuleModel.is_active == True
            ).all()
            
            for db_rule in db_rules:
                rule_type = QualityRuleType(db_rule.rule_type)
                config = json.loads(db_rule.rule_config) if db_rule.rule_config else {}
                
                rule = QualityRule(
                    rule_id=db_rule.rule_id,
                    rule_type=rule_type,
                    target_table=db_rule.target_table,
                    target_field=db_rule.target_field,
                    config=config,
                    severity=db_rule.severity
                )
                
                self.add_rule(rule)
            
            logger.info(f"从数据库加载了 {len(db_rules)} 条质量规则")
            
        except Exception as e:
            logger.error(f"从数据库加载质量规则失败: {e}")
    
    def check_data_quality(self, table_name: str, data: List[Dict[str, Any]], 
                          batch_id: str = None) -> Dict[str, Any]:
        """
        检查数据质量
        
        Args:
            table_name: 表名
            data: 数据列表
            batch_id: 批次ID
            
        Returns:
            质量检查结果
        """
        # 获取适用于该表的规则
        applicable_rules = [rule for rule in self.rules if rule.target_table == table_name]
        
        if not applicable_rules:
            logger.info(f"表 {table_name} 没有配置质量规则")
            return {
                'table_name': table_name,
                'total_records': len(data),
                'passed_records': len(data),
                'failed_records': 0,
                'pass_rate': 1.0,
                'rule_results': [],
                'error_details': []
            }
        
        total_records = len(data)
        passed_records = 0
        failed_records = 0
        error_details = []
        rule_results = []
        
        # 对每条记录进行质量检查
        for record_index, record in enumerate(data):
            record_passed = True
            record_errors = []
            record_warnings = []
            
            # 应用所有规则
            for rule in applicable_rules:
                validation_result = rule.validate(record, self.db_session)
                
                if not validation_result['passed']:
                    record_passed = False
                    record_errors.extend(validation_result['errors'])
                
                if validation_result.get('warnings'):
                    record_warnings.extend(validation_result['warnings'])
                
                # 收集规则级别的结果
                rule_results.append({
                    'rule_id': rule.rule_id,
                    'rule_type': rule.rule_type.value,
                    'target_field': rule.target_field,
                    'passed': validation_result['passed'],
                    'record_index': record_index,
                    'errors': validation_result['errors'],
                    'warnings': validation_result.get('warnings', [])
                })
            
            if record_passed:
                passed_records += 1
            else:
                failed_records += 1
                error_details.append({
                    'record_index': record_index,
                    'record_data': record,
                    'errors': record_errors,
                    'warnings': record_warnings
                })
        
        # 计算通过率
        pass_rate = passed_records / total_records if total_records > 0 else 0
        
        # 保存检查结果到数据库
        if self.db_session and batch_id:
            self._save_check_results(table_name, batch_id, total_records, 
                                   passed_records, failed_records, pass_rate, 
                                   error_details, applicable_rules)
        
        result = {
            'table_name': table_name,
            'batch_id': batch_id,
            'total_records': total_records,
            'passed_records': passed_records,
            'failed_records': failed_records,
            'pass_rate': pass_rate,
            'checked_at': datetime.now().isoformat(),
            'rule_results': rule_results,
            'error_details': error_details[:100],  # 限制错误详情数量
            'quality_summary': {
                'critical_errors': len([r for r in rule_results if not r['passed'] and any('ERROR' in e for e in r['errors'])]),
                'warnings': len([r for r in rule_results if r.get('warnings')])
            }
        }
        
        logger.info(f"表 {table_name} 质量检查完成: 通过率 {pass_rate:.2%} ({passed_records}/{total_records})")
        
        return result
    
    def _save_check_results(self, table_name: str, batch_id: str, total_records: int,
                           passed_records: int, failed_records: int, pass_rate: float,
                           error_details: List[Dict[str, Any]], rules: List[QualityRule]):
        """保存检查结果到数据库"""
        try:
            for rule in rules:
                # 为每个规则创建检查结果记录
                check_result = QualityCheckResult(
                    check_id=f"{batch_id}_{rule.rule_id}",
                    rule_id=rule.rule_id,
                    data_batch_id=batch_id,
                    table_name=table_name,
                    total_records=total_records,
                    passed_records=passed_records,
                    failed_records=failed_records,
                    pass_rate=pass_rate,
                    error_details=json.dumps(error_details, ensure_ascii=False),
                    checked_at=datetime.now()
                )
                
                self.db_session.add(check_result)
            
            self.db_session.commit()
            logger.info(f"质量检查结果已保存: {batch_id}")
            
        except Exception as e:
            logger.error(f"保存质量检查结果失败: {e}")
            self.db_session.rollback()
    
    def get_quality_report(self, table_name: str = None, 
                          start_date: datetime = None, 
                          end_date: datetime = None) -> Dict[str, Any]:
        """
        获取质量报告
        
        Args:
            table_name: 表名（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            质量报告
        """
        if not self.db_session:
            return {'error': '缺少数据库会话'}
        
        try:
            query = self.db_session.query(QualityCheckResult)
            
            if table_name:
                query = query.filter(QualityCheckResult.table_name == table_name)
            
            if start_date:
                query = query.filter(QualityCheckResult.checked_at >= start_date)
            
            if end_date:
                query = query.filter(QualityCheckResult.checked_at <= end_date)
            
            results = query.order_by(QualityCheckResult.checked_at.desc()).all()
            
            # 聚合统计
            total_checks = len(results)
            avg_pass_rate = sum(r.pass_rate for r in results) / total_checks if total_checks > 0 else 0
            
            # 按表分组的统计
            table_stats = {}
            for result in results:
                table = result.table_name
                if table not in table_stats:
                    table_stats[table] = {
                        'check_count': 0,
                        'avg_pass_rate': 0,
                        'total_records': 0,
                        'total_passed': 0,
                        'total_failed': 0
                    }
                
                stats = table_stats[table]
                stats['check_count'] += 1
                stats['avg_pass_rate'] += result.pass_rate
                stats['total_records'] += result.total_records
                stats['total_passed'] += result.passed_records
                stats['total_failed'] += result.failed_records
            
            # 计算平均值
            for stats in table_stats.values():
                if stats['check_count'] > 0:
                    stats['avg_pass_rate'] /= stats['check_count']
            
            return {
                'summary': {
                    'total_checks': total_checks,
                    'avg_pass_rate': avg_pass_rate,
                    'report_period': {
                        'start': start_date.isoformat() if start_date else None,
                        'end': end_date.isoformat() if end_date else None
                    }
                },
                'table_statistics': table_stats,
                'recent_checks': [
                    {
                        'check_id': r.check_id,
                        'table_name': r.table_name,
                        'pass_rate': r.pass_rate,
                        'total_records': r.total_records,
                        'checked_at': r.checked_at.isoformat()
                    }
                    for r in results[:20]  # 最近20次检查
                ]
            }
            
        except Exception as e:
            logger.error(f"获取质量报告失败: {e}")
            return {'error': str(e)}


class QualityRuleBuilder:
    """质量规则构建器"""
    
    def __init__(self):
        self.rule_data = {}
    
    def rule_id(self, rule_id: str):
        """设置规则ID"""
        self.rule_data['rule_id'] = rule_id
        return self
    
    def target(self, table: str, field: str):
        """设置目标表和字段"""
        self.rule_data['target_table'] = table
        self.rule_data['target_field'] = field
        return self
    
    def not_null(self):
        """非空规则"""
        self.rule_data['rule_type'] = QualityRuleType.NOT_NULL
        self.rule_data['config'] = {}
        return self
    
    def unique(self):
        """唯一性规则"""
        self.rule_data['rule_type'] = QualityRuleType.UNIQUE
        self.rule_data['config'] = {}
        return self
    
    def range(self, min_val: float = None, max_val: float = None):
        """范围规则"""
        self.rule_data['rule_type'] = QualityRuleType.RANGE
        self.rule_data['config'] = {'min': min_val, 'max': max_val}
        return self
    
    def pattern(self, regex_pattern: str):
        """正则模式规则"""
        self.rule_data['rule_type'] = QualityRuleType.PATTERN
        self.rule_data['config'] = {'pattern': regex_pattern}
        return self
    
    def length(self, min_length: int = None, max_length: int = None):
        """长度规则"""
        self.rule_data['rule_type'] = QualityRuleType.LENGTH
        self.rule_data['config'] = {'min_length': min_length, 'max_length': max_length}
        return self
    
    def format(self, format_type: str, **kwargs):
        """格式规则"""
        self.rule_data['rule_type'] = QualityRuleType.FORMAT
        config = {'format_type': format_type}
        config.update(kwargs)
        self.rule_data['config'] = config
        return self
    
    def enum(self, allowed_values: List[Any]):
        """枚举规则"""
        self.rule_data['rule_type'] = QualityRuleType.ENUM
        self.rule_data['config'] = {'allowed_values': allowed_values}
        return self
    
    def reference(self, ref_table: str, ref_field: str):
        """引用规则"""
        self.rule_data['rule_type'] = QualityRuleType.REFERENCE
        self.rule_data['config'] = {'ref_table': ref_table, 'ref_field': ref_field}
        return self
    
    def custom(self, custom_function: Callable):
        """自定义规则"""
        self.rule_data['rule_type'] = QualityRuleType.CUSTOM
        self.rule_data['config'] = {'custom_function': custom_function}
        return self
    
    def severity(self, severity: str):
        """设置严重程度"""
        self.rule_data['severity'] = severity
        return self
    
    def build(self) -> QualityRule:
        """构建质量规则"""
        required_fields = ['rule_id', 'rule_type', 'target_table', 'target_field']
        
        for field in required_fields:
            if field not in self.rule_data:
                raise ValueError(f"缺少必需字段: {field}")
        
        return QualityRule(
            rule_id=self.rule_data['rule_id'],
            rule_type=self.rule_data['rule_type'],
            target_table=self.rule_data['target_table'],
            target_field=self.rule_data['target_field'],
            config=self.rule_data.get('config', {}),
            severity=self.rule_data.get('severity', 'ERROR')
        )


# 预定义的常用质量规则
class CommonQualityRules:
    """常用质量规则"""
    
    @staticmethod
    def news_title_rules() -> List[QualityRule]:
        """新闻标题质量规则"""
        return [
            QualityRuleBuilder()
            .rule_id("news_title_not_null")
            .target("news_unified", "title")
            .not_null()
            .severity("ERROR")
            .build(),
            
            QualityRuleBuilder()
            .rule_id("news_title_length")
            .target("news_unified", "title")
            .length(min_length=5, max_length=200)
            .severity("WARNING")
            .build()
        ]
    
    @staticmethod
    def news_url_rules() -> List[QualityRule]:
        """新闻URL质量规则"""
        return [
            QualityRuleBuilder()
            .rule_id("news_url_not_null")
            .target("news_unified", "url")
            .not_null()
            .severity("ERROR")
            .build(),
            
            QualityRuleBuilder()
            .rule_id("news_url_format")
            .target("news_unified", "url")
            .format("url")
            .severity("ERROR")
            .build(),
            
            QualityRuleBuilder()
            .rule_id("news_url_unique")
            .target("news_unified", "url")
            .unique()
            .severity("WARNING")
            .build()
        ]
    
    @staticmethod
    def news_sentiment_rules() -> List[QualityRule]:
        """新闻情感分数质量规则"""
        return [
            QualityRuleBuilder()
            .rule_id("news_sentiment_range")
            .target("news_unified", "sentiment_score")
            .range(min_val=-1.0, max_val=1.0)
            .severity("ERROR")
            .build()
        ] 