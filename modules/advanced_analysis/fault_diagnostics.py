#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
故障诊断系统
基于异常模式识别和根因分析
"""

import numpy as np
import pandas as pd
from scipy import signal, stats
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import json
from datetime import datetime

class FaultDiagnosticSystem:
    """故障诊断系统"""
    
    def __init__(self):
        """初始化故障诊断系统"""
        # 故障模式库
        self.fault_patterns = {
            '启动延迟': {
                'symptoms': ['启动时长>5秒', '达峰时长>15秒'],
                'possible_causes': [
                    '点火层配方问题',
                    '引火药失效或受潮',
                    '密封不良导致初始压力不足',
                    '环境温度过低'
                ],
                'recommendations': [
                    '检查A层配方，增加点火药含量',
                    '检查原料储存条件，确保干燥',
                    '检查产品密封性',
                    '预热或改进低温启动配方'
                ]
            },
            '流量波动大': {
                'symptoms': ['CV值>15%', '异常次数>5'],
                'possible_causes': [
                    '配方混合不均匀',
                    '压制密度不一致',
                    '原料粒度分布不均',
                    '反应通道堵塞'
                ],
                'recommendations': [
                    '改进混料工艺，延长混合时间',
                    '优化压制工艺参数',
                    '严格控制原料粒度',
                    '检查产品内部结构'
                ]
            },
            '提前熄灭': {
                'symptoms': ['产氧时间<22分钟', '末期流量急剧下降'],
                'possible_causes': [
                    '氧化剂含量不足',
                    '燃料过多',
                    '反应抑制剂过量',
                    'C3层配方问题'
                ],
                'recommendations': [
                    '增加氯酸钠含量',
                    '减少铁粉含量',
                    '调整玻璃纤维比例',
                    '重新设计C3层配方'
                ]
            },
            '温度过高': {
                'symptoms': ['外壳温度>230°C', '隔热垫温度>150°C'],
                'possible_causes': [
                    '反应过于剧烈',
                    '散热设计不良',
                    '隔热材料失效',
                    '配方过于活泼'
                ],
                'recommendations': [
                    '降低配方活性，增加缓和剂',
                    '改进散热结构设计',
                    '更换隔热材料',
                    '优化各层配方比例'
                ]
            },
            '达标率低': {
                'symptoms': ['达标率<95%', '累计流量不足'],
                'possible_causes': [
                    '总体配方设计问题',
                    '原料纯度不够',
                    '工艺控制不稳定',
                    '生产过程偏差'
                ],
                'recommendations': [
                    '全面审查配方设计',
                    '检查原料质量证书',
                    '加强工艺过程控制',
                    '提高生产一致性'
                ]
            },
            '中期凹陷': {
                'symptoms': ['600-900秒流量低于基准', '中期异常集中'],
                'possible_causes': [
                    'C1/C2层过渡问题',
                    '中间层配方活性不足',
                    '压制分层现象',
                    '原料分布不均'
                ],
                'recommendations': [
                    '优化层间过渡配方',
                    '提高C1层末端活性',
                    '改进分层压制工艺',
                    '加强混料均匀性'
                ]
            }
        }
        
        # AS9100D要求的诊断准确率
        self.min_diagnosis_confidence = 0.7
        
    def diagnose(self, sample_data):
        """
        对单个样品进行故障诊断
        
        Parameters:
        sample_data: dict或DataFrame，样品数据
        
        Returns:
        dict: 诊断结果
        """
        # 转换为字典
        if isinstance(sample_data, pd.DataFrame):
            if len(sample_data) > 1:
                sample_data = sample_data.iloc[0]
            sample_data = sample_data.to_dict()
        
        diagnosis_result = {
            'sample_id': sample_data.get('样品编号', 'Unknown'),
            'diagnosis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'detected_faults': [],
            'recommendations': [],
            'confidence': 0,
            'severity': 'NORMAL'
        }
        
        # 1. 症状识别
        symptoms = self.identify_symptoms(sample_data)
        
        if not symptoms:
            diagnosis_result['summary'] = '未检测到明显故障'
            diagnosis_result['confidence'] = 1.0
            return diagnosis_result
        
        # 2. 故障匹配
        matched_faults = self.match_faults(symptoms)
        
        # 3. 根因分析
        for fault_name, match_info in matched_faults.items():
            fault_detail = {
                'fault_type': fault_name,
                'confidence': match_info['confidence'],
                'matched_symptoms': match_info['matched_symptoms'],
                'possible_causes': self.fault_patterns[fault_name]['possible_causes'],
                'recommendations': self.fault_patterns[fault_name]['recommendations']
            }
            diagnosis_result['detected_faults'].append(fault_detail)
            diagnosis_result['recommendations'].extend(
                self.fault_patterns[fault_name]['recommendations']
            )
        
        # 4. 计算总体置信度和严重程度
        if matched_faults:
            diagnosis_result['confidence'] = np.mean([
                f['confidence'] for f in matched_faults.values()
            ])
            diagnosis_result['severity'] = self.assess_severity(symptoms, matched_faults)
        
        # 5. 去重和排序建议
        diagnosis_result['recommendations'] = list(set(diagnosis_result['recommendations']))
        
        # 6. 生成诊断总结
        diagnosis_result['summary'] = self.generate_summary(diagnosis_result)
        
        # 7. AS9100D合规性检查
        diagnosis_result['AS9100D_action'] = self.determine_as9100d_action(diagnosis_result)
        
        return diagnosis_result
    
    def identify_symptoms(self, data):
        """识别症状"""
        symptoms = []
        
        # 启动性能
        if data.get('启动时长(秒)', 0) > 5:
            symptoms.append('启动时长>5秒')
        if data.get('达峰时长(秒)', 0) > 15:
            symptoms.append('达峰时长>15秒')
        
        # 产氧时间
        duration = data.get('产氧时间(分钟)', 0)
        if duration > 0 and duration < 22:
            symptoms.append('产氧时间<22分钟')
        
        # 温度
        if data.get('外壳最高温度(°C)', 0) > 230:
            symptoms.append('外壳温度>230°C')
        if data.get('隔热垫外最高温度(°C)', 0) > 150:
            symptoms.append('隔热垫温度>150°C')
        
        # 达标率
        if data.get('达标率(%)', 100) < 95:
            symptoms.append('达标率<95%')
        
        # 稳定性（需要CV值）
        # 简化处理：用异常次数估算
        if data.get('异常次数', 0) > 5:
            symptoms.append('异常次数>5')
            symptoms.append('CV值>15%')  # 假设异常多则CV值大
        
        # 流量特征（需要详细数据）
        if data.get('异常持续时间(秒)', 0) > 60:
            symptoms.append('中期异常集中')
            symptoms.append('600-900秒流量低于基准')
        
        # 累计流量
        expected_oxygen = duration * 4.5 if duration > 0 else 100  # 简单估算
        if data.get('累计流量(升)', 0) < expected_oxygen * 0.9:
            symptoms.append('累计流量不足')
        
        return symptoms
    
    def match_faults(self, symptoms):
        """匹配故障模式"""
        matched = {}
        
        for fault_name, fault_info in self.fault_patterns.items():
            fault_symptoms = fault_info['symptoms']
            
            # 计算匹配度
            matched_symptoms = []
            for symptom in fault_symptoms:
                if symptom in symptoms:
                    matched_symptoms.append(symptom)
            
            if matched_symptoms:
                # 计算置信度
                confidence = len(matched_symptoms) / len(fault_symptoms)
                
                # 如果有额外的相关症状，提高置信度
                related_symptoms = set(symptoms) - set(fault_symptoms)
                if related_symptoms:
                    confidence = min(confidence * 1.1, 1.0)
                
                matched[fault_name] = {
                    'confidence': confidence,
                    'matched_symptoms': matched_symptoms
                }
        
        # 按置信度排序
        matched = dict(sorted(matched.items(), key=lambda x: x[1]['confidence'], reverse=True))
        
        return matched
    
    def assess_severity(self, symptoms, matched_faults):
        """评估严重程度"""
        # 基于症状数量和故障类型评估
        severity_score = 0
        
        # 关键故障权重更高
        critical_faults = ['温度过高', '提前熄灭', '达标率低']
        for fault in matched_faults:
            if fault in critical_faults:
                severity_score += 3
            else:
                severity_score += 1
        
        # 症状数量影响
        severity_score += len(symptoms) * 0.5
        
        # 分级
        if severity_score >= 5:
            return 'CRITICAL'
        elif severity_score >= 3:
            return 'HIGH'
        elif severity_score >= 1:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def generate_summary(self, diagnosis_result):
        """生成诊断总结"""
        if not diagnosis_result['detected_faults']:
            return "产品性能正常，未发现明显故障。"
        
        # 主要故障
        main_fault = diagnosis_result['detected_faults'][0]
        summary = f"检测到{len(diagnosis_result['detected_faults'])}个潜在问题。"
        summary += f"最可能的故障是【{main_fault['fault_type']}】"
        summary += f"（置信度：{main_fault['confidence']:.1%}）。"
        
        # 严重程度
        severity_text = {
            'CRITICAL': '需要立即处理',
            'HIGH': '建议尽快改进',
            'MEDIUM': '需要关注',
            'LOW': '轻微问题',
            'NORMAL': '正常'
        }
        
        summary += f"问题严重程度：{severity_text[diagnosis_result['severity']]}。"
        
        return summary
    
    def determine_as9100d_action(self, diagnosis_result):
        """确定AS9100D要求的行动"""
        severity = diagnosis_result['severity']
        confidence = diagnosis_result['confidence']
        
        actions = {
            'action_required': False,
            'action_type': None,
            'description': ''
        }
        
        if severity == 'CRITICAL':
            actions['action_required'] = True
            actions['action_type'] = 'CORRECTIVE_ACTION'
            actions['description'] = '需要立即采取纠正措施并记录'
        elif severity == 'HIGH' and confidence > self.min_diagnosis_confidence:
            actions['action_required'] = True
            actions['action_type'] = 'PREVENTIVE_ACTION'
            actions['description'] = '需要制定预防措施计划'
        elif severity == 'MEDIUM':
            actions['action_type'] = 'MONITORING'
            actions['description'] = '加强监控，收集更多数据'
        else:
            actions['action_type'] = 'NONE'
            actions['description'] = '继续正常生产'
        
        return actions
    
    def batch_diagnose(self, samples_df):
        """批量诊断"""
        results = []
        
        for idx, row in samples_df.iterrows():
            diagnosis = self.diagnose(row)
            results.append(diagnosis)
        
        # 统计分析
        summary = self.analyze_batch_results(results)
        
        return {
            'individual_results': results,
            'summary': summary
        }
    
    def analyze_batch_results(self, results):
        """分析批量诊断结果"""
        summary = {
            'total_samples': len(results),
            'fault_distribution': {},
            'severity_distribution': {},
            'common_recommendations': [],
            'systemic_issues': []
        }
        
        # 故障分布
        all_faults = []
        all_recommendations = []
        severity_counts = {'NORMAL': 0, 'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
        
        for result in results:
            severity_counts[result.get('severity', 'NORMAL')] += 1
            
            for fault in result.get('detected_faults', []):
                all_faults.append(fault['fault_type'])
            
            all_recommendations.extend(result.get('recommendations', []))
        
        # 统计故障频率
        fault_counts = pd.Series(all_faults).value_counts()
        summary['fault_distribution'] = fault_counts.to_dict()
        
        # 严重程度分布
        summary['severity_distribution'] = severity_counts
        
        # 最常见的建议（前5个）
        rec_counts = pd.Series(all_recommendations).value_counts()
        summary['common_recommendations'] = rec_counts.head(5).index.tolist()
        
        # 识别系统性问题（超过30%的样品有相同故障）
        threshold = len(results) * 0.3
        for fault, count in fault_counts.items():
            if count > threshold:
                summary['systemic_issues'].append({
                    'issue': fault,
                    'affected_samples': count,
                    'percentage': round(count / len(results) * 100, 1)
                })
        
        return summary
    
    def generate_diagnostic_report(self, diagnosis_result, output_path=None):
        """生成诊断报告"""
        report = []
        report.append("=" * 60)
        report.append("故障诊断报告")
        report.append("=" * 60)
        report.append(f"样品编号: {diagnosis_result['sample_id']}")
        report.append(f"诊断时间: {diagnosis_result['diagnosis_time']}")
        report.append(f"置信度: {diagnosis_result['confidence']:.1%}")
        report.append(f"严重程度: {diagnosis_result['severity']}")
        
        report.append(f"\n【诊断总结】")
        report.append(diagnosis_result['summary'])
        
        if diagnosis_result['detected_faults']:
            report.append(f"\n【检测到的故障】")
            for i, fault in enumerate(diagnosis_result['detected_faults'], 1):
                report.append(f"\n{i}. {fault['fault_type']} (置信度: {fault['confidence']:.1%})")
                report.append("   匹配症状:")
                for symptom in fault['matched_symptoms']:
                    report.append(f"   - {symptom}")
                report.append("   可能原因:")
                for cause in fault['possible_causes'][:3]:  # 只显示前3个
                    report.append(f"   - {cause}")
        
        report.append(f"\n【改进建议】")
        for i, rec in enumerate(diagnosis_result['recommendations'][:5], 1):  # 只显示前5个
            report.append(f"{i}. {rec}")
        
        as9100d = diagnosis_result.get('AS9100D_action', {})
        if as9100d.get('action_required'):
            report.append(f"\n【AS9100D要求】")
            report.append(f"行动类型: {as9100d['action_type']}")
            report.append(f"说明: {as9100d['description']}")
        
        report_text = '\n'.join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text