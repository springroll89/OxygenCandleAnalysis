#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
波谷规律分析模块
用于检测和分析氧烛流量曲线中的波谷特征
"""

import numpy as np
import pandas as pd
from scipy import signal
from scipy.integrate import trapezoid
import json
from datetime import datetime

class ValleyAnalyzer:
    """波谷规律分析器"""
    
    def __init__(self, baseline_threshold=0.95):
        """
        初始化波谷分析器
        
        Parameters:
        baseline_threshold: 判定波谷的阈值（相对于基准曲线的比例）
        """
        self.baseline_threshold = baseline_threshold
        self.valley_records = []
        
    def detect_valleys(self, time_data, flow_data, baseline_data, cumulative_oxygen=None):
        """
        检测流量曲线中的所有波谷
        
        Parameters:
        time_data: 时间序列数据（秒）
        flow_data: 实际流量数据（L/min）
        baseline_data: 基准流量数据（L/min）
        cumulative_oxygen: 累积产氧量数据（L）
        
        Returns:
        list: 波谷列表，每个波谷包含详细信息
        """
        valleys = []
        
        # 1. 找出所有低于基准的连续时段
        below_baseline = flow_data < (baseline_data * self.baseline_threshold)
        
        # 2. 识别连续的波谷段
        valley_segments = []
        in_valley = False
        start_idx = None
        
        for i in range(len(below_baseline)):
            if below_baseline[i] and not in_valley:
                in_valley = True
                start_idx = i
            elif not below_baseline[i] and in_valley:
                in_valley = False
                if start_idx is not None and i - start_idx > 5:  # 至少持续2.5秒（5个数据点）
                    valley_segments.append((start_idx, i-1))
                start_idx = None
        
        # 处理最后一个波谷
        if in_valley and start_idx is not None:
            valley_segments.append((start_idx, len(below_baseline)-1))
        
        # 3. 分析每个波谷段
        for seg_start, seg_end in valley_segments:
            valley_info = self._analyze_valley_segment(
                time_data, flow_data, baseline_data, 
                seg_start, seg_end, cumulative_oxygen
            )
            if valley_info['depth'] > 0.1:  # 只记录深度大于0.1 L/min的波谷
                valleys.append(valley_info)
        
        # 4. 合并邻近的波谷（间隔小于10秒的）
        valleys = self._merge_nearby_valleys(valleys)
        
        return valleys
    
    def _analyze_valley_segment(self, time_data, flow_data, baseline_data, 
                                start_idx, end_idx, cumulative_oxygen):
        """分析单个波谷段的特征"""
        
        # 波谷时间范围
        start_time = time_data[start_idx]
        end_time = time_data[end_idx]
        duration = end_time - start_time
        
        # 波谷中心时间（最低点）
        valley_flow = flow_data[start_idx:end_idx+1]
        valley_baseline = baseline_data[start_idx:end_idx+1]
        min_idx = np.argmin(valley_flow)
        center_time = time_data[start_idx + min_idx]
        
        # 波谷深度（最低点与基准的差值）
        min_flow = valley_flow[min_idx]
        baseline_at_min = valley_baseline[min_idx]
        depth = baseline_at_min - min_flow
        
        # 波谷面积（产氧损失量）
        time_segment = time_data[start_idx:end_idx+1]
        flow_deficit = np.maximum(valley_baseline - valley_flow, 0)
        oxygen_loss = trapezoid(flow_deficit, time_segment) / 60  # 转换为升
        
        # 对应的累积产氧量（用于计算燃烧深度）
        if cumulative_oxygen is not None and start_idx < len(cumulative_oxygen):
            oxygen_at_valley = cumulative_oxygen[start_idx + min_idx]
        else:
            oxygen_at_valley = None
        
        # 波谷形态特征
        shape_features = self._analyze_valley_shape(valley_flow, valley_baseline)
        
        return {
            'start_time': round(start_time, 1),
            'end_time': round(end_time, 1),
            'center_time': round(center_time, 1),
            'duration': round(duration, 1),
            'depth': round(depth, 3),
            'min_flow': round(min_flow, 3),
            'baseline_at_valley': round(baseline_at_min, 3),
            'oxygen_loss': round(oxygen_loss, 2),
            'oxygen_at_valley': round(oxygen_at_valley, 1) if oxygen_at_valley else None,
            'shape': shape_features
        }
    
    def _analyze_valley_shape(self, valley_flow, valley_baseline):
        """分析波谷的形态特征"""
        
        # 计算波谷的对称性
        min_idx = np.argmin(valley_flow)
        left_part = valley_flow[:min_idx]
        right_part = valley_flow[min_idx+1:]
        
        if len(left_part) > 0 and len(right_part) > 0:
            # 比较左右两侧的平均斜率
            left_slope = (valley_flow[min_idx] - valley_flow[0]) / max(len(left_part), 1)
            right_slope = (valley_flow[-1] - valley_flow[min_idx]) / max(len(right_part), 1)
            
            if abs(left_slope) > abs(right_slope) * 1.5:
                shape_type = "陡降缓升"
            elif abs(right_slope) > abs(left_slope) * 1.5:
                shape_type = "缓降陡升"
            else:
                shape_type = "对称"
        else:
            shape_type = "不规则"
        
        # 计算相对深度（相对于基准的百分比）
        relative_depth = (valley_baseline - valley_flow) / valley_baseline
        max_relative_depth = np.max(relative_depth)
        
        return {
            'type': shape_type,
            'relative_depth': round(max_relative_depth * 100, 1)  # 百分比
        }
    
    def _merge_nearby_valleys(self, valleys, merge_threshold=10):
        """合并邻近的波谷（间隔小于阈值的）"""
        if len(valleys) <= 1:
            return valleys
        
        merged = []
        current = valleys[0]
        
        for next_valley in valleys[1:]:
            # 检查是否应该合并
            if next_valley['start_time'] - current['end_time'] < merge_threshold:
                # 合并波谷
                current = {
                    'start_time': current['start_time'],
                    'end_time': next_valley['end_time'],
                    'center_time': (current['center_time'] + next_valley['center_time']) / 2,
                    'duration': next_valley['end_time'] - current['start_time'],
                    'depth': max(current['depth'], next_valley['depth']),
                    'min_flow': min(current['min_flow'], next_valley['min_flow']),
                    'baseline_at_valley': (current['baseline_at_valley'] + next_valley['baseline_at_valley']) / 2,
                    'oxygen_loss': current['oxygen_loss'] + next_valley['oxygen_loss'],
                    'oxygen_at_valley': (current['oxygen_at_valley'] + next_valley['oxygen_at_valley']) / 2 
                                      if current['oxygen_at_valley'] and next_valley['oxygen_at_valley'] else None,
                    'shape': {'type': '复合波谷', 'relative_depth': max(current['shape']['relative_depth'], 
                                                                        next_valley['shape']['relative_depth'])}
                }
            else:
                merged.append(current)
                current = next_valley
        
        merged.append(current)
        return merged
    
    def correlate_with_burn_depth(self, valley, scale_df, total_oxygen):
        """
        将波谷位置与燃烧深度关联
        
        Parameters:
        valley: 波谷信息
        scale_df: 刻度表数据
        total_oxygen: 总产氧量
        
        Returns:
        dict: 包含燃烧深度和物理位置的信息
        """
        if valley['oxygen_at_valley'] is None or total_oxygen <= 0:
            return {'burn_depth': None, 'position': '未知'}
        
        # 计算产氧百分比
        oxygen_percentage = valley['oxygen_at_valley'] / total_oxygen
        
        # 根据刻度表插值计算燃烧深度
        if not scale_df.empty and '有效燃烧百分比' in scale_df.columns:
            percentages = scale_df['有效燃烧百分比'].values
            depths = scale_df['刻度值/mm'].values
            
            # 线性插值
            if oxygen_percentage <= percentages.min():
                burn_depth = depths[0]
            elif oxygen_percentage >= percentages.max():
                burn_depth = depths[-1]
            else:
                burn_depth = np.interp(oxygen_percentage, percentages, depths)
            
            # 确定物理位置
            if '大致位置' in scale_df.columns:
                closest_idx = np.abs(scale_df['刻度值/mm'] - burn_depth).idxmin()
                position = scale_df.loc[closest_idx, '大致位置']
            else:
                # 简单分层
                if burn_depth < 50:
                    position = "A、B层"
                elif burn_depth < 100:
                    position = "C1层"
                elif burn_depth < 150:
                    position = "C2层"
                else:
                    position = "C3层"
        else:
            # 简单估算
            burn_depth = oxygen_percentage * 200  # 假设总深度200mm
            if burn_depth < 50:
                position = "A、B层"
            elif burn_depth < 100:
                position = "C1层"
            elif burn_depth < 150:
                position = "C2层"
            else:
                position = "C3层"
        
        return {
            'burn_depth': round(burn_depth, 1),
            'position': position,
            'oxygen_percentage': round(oxygen_percentage * 100, 1)
        }
    
    def analyze_batch_valleys(self, reports_data):
        """
        批量分析多个产品的波谷规律
        
        Parameters:
        reports_data: 包含多个产品波谷数据的列表
        
        Returns:
        dict: 波谷规律统计结果
        """
        all_valleys = []
        
        for report in reports_data:
            if 'valleys' in report and report['valleys']:
                for valley in report['valleys']:
                    valley_record = {
                        'product_id': report['product_id'],
                        'formula': report.get('formula', ''),
                        'process': report.get('process', ''),
                        **valley
                    }
                    all_valleys.append(valley_record)
        
        if not all_valleys:
            return None
        
        # 转换为DataFrame便于分析
        valleys_df = pd.DataFrame(all_valleys)
        
        # 统计分析
        statistics = {
            'total_products': len(reports_data),
            'products_with_valleys': len(valleys_df['product_id'].unique()),
            'total_valleys': len(valleys_df),
            'avg_valleys_per_product': round(len(valleys_df) / len(valleys_df['product_id'].unique()), 1)
        }
        
        # 位置分布分析
        if 'burn_depth' in valleys_df.columns:
            depth_stats = valleys_df.groupby(pd.cut(valleys_df['burn_depth'], 
                                                    bins=[0, 50, 100, 150, 200],
                                                    labels=['0-50mm', '50-100mm', '100-150mm', '150-200mm'])).size()
            statistics['depth_distribution'] = depth_stats.to_dict()
            
            # 找出高发区
            most_common_range = depth_stats.idxmax()
            statistics['most_common_depth_range'] = most_common_range
        
        # 深度统计
        statistics['avg_valley_depth'] = round(valleys_df['depth'].mean(), 3)
        statistics['max_valley_depth'] = round(valleys_df['depth'].max(), 3)
        statistics['total_oxygen_loss'] = round(valleys_df['oxygen_loss'].sum(), 1)
        
        # 位置一致性分析
        if 'position' in valleys_df.columns:
            position_counts = valleys_df['position'].value_counts()
            most_common_position = position_counts.index[0]
            consistency = position_counts.iloc[0] / len(valleys_df) * 100
            
            statistics['most_common_position'] = most_common_position
            statistics['position_consistency'] = round(consistency, 1)
        
        # 配方相关性分析
        if 'formula' in valleys_df.columns:
            formula_valley_counts = valleys_df.groupby('formula').size()
            statistics['formula_correlation'] = formula_valley_counts.to_dict()
        
        return statistics
    
    def generate_valley_report(self, product_data, valleys, statistics=None):
        """
        生成波谷分析报告
        
        Parameters:
        product_data: 产品基本信息
        valleys: 检测到的波谷列表
        statistics: 批量分析统计结果（可选）
        
        Returns:
        dict: 完整的波谷分析报告
        """
        report = {
            'product_id': product_data.get('product_id', ''),
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'valley_count': len(valleys),
            'valleys': valleys
        }
        
        if valleys:
            # 主波谷（最深的）
            main_valley = max(valleys, key=lambda x: x['depth'])
            report['main_valley'] = {
                'time': main_valley['center_time'],
                'depth': main_valley['depth'],
                'oxygen_loss': main_valley['oxygen_loss'],
                'position': main_valley.get('position', '未知')
            }
            
            # 总产氧损失
            report['total_oxygen_loss'] = sum(v['oxygen_loss'] for v in valleys)
            
            # 波谷特征总结
            report['summary'] = self._generate_summary(valleys)
        
        # 添加批量统计结果（如果有）
        if statistics:
            report['batch_statistics'] = statistics
            report['recommendations'] = self._generate_recommendations(valleys, statistics)
        
        return report
    
    def _generate_summary(self, valleys):
        """生成波谷特征总结"""
        if not valleys:
            return "无波谷"
        
        summary = []
        
        # 波谷数量
        if len(valleys) == 1:
            summary.append("单波谷")
        elif len(valleys) == 2:
            summary.append("双波谷")
        else:
            summary.append(f"多波谷({len(valleys)}个)")
        
        # 主要问题时段
        main_valley = max(valleys, key=lambda x: x['depth'])
        if main_valley['center_time'] < 300:
            summary.append("早期异常")
        elif main_valley['center_time'] < 900:
            summary.append("中期异常")
        else:
            summary.append("后期异常")
        
        # 严重程度
        if main_valley['depth'] > 1.0:
            summary.append("严重偏离")
        elif main_valley['depth'] > 0.5:
            summary.append("中度偏离")
        else:
            summary.append("轻微偏离")
        
        return "，".join(summary)
    
    def _generate_recommendations(self, valleys, statistics):
        """基于波谷分析生成改进建议"""
        recommendations = []
        
        # 基于位置的建议
        if statistics and 'most_common_position' in statistics:
            position = statistics['most_common_position']
            if 'C1' in position:
                recommendations.append("优化C1层配方或压制密度")
            elif 'C2' in position:
                recommendations.append("检查C2层原料混合均匀性")
            elif 'A、B' in position:
                recommendations.append("调整启动段配方活性")
        
        # 基于深度的建议
        if valleys:
            max_depth = max(v['depth'] for v in valleys)
            if max_depth > 1.0:
                recommendations.append("增加对应深度的反应物含量")
            if len(valleys) > 2:
                recommendations.append("改进整体混料工艺，确保均匀性")
        
        # 基于一致性的建议
        if statistics and statistics.get('position_consistency', 0) > 70:
            recommendations.append("该位置为共性问题，需要系统性改进")
        
        return recommendations
    
    def export_valley_analysis(self, report, output_file):
        """
        导出波谷分析结果
        
        Parameters:
        report: 波谷分析报告
        output_file: 输出文件路径（JSON格式）
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"波谷分析报告已导出至: {output_file}")


# 使用示例
if __name__ == "__main__":
    # 创建分析器
    analyzer = ValleyAnalyzer(baseline_threshold=0.95)
    
    # 模拟数据
    time = np.linspace(0, 1400, 2800)
    
    # 创建带波谷的流量曲线
    flow = 4.0 * np.ones_like(time)
    
    # 添加两个波谷
    valley1_mask = (time > 400) & (time < 450)
    flow[valley1_mask] = 3.2 - 0.5 * np.sin((time[valley1_mask] - 400) * np.pi / 50)
    
    valley2_mask = (time > 800) & (time < 860)
    flow[valley2_mask] = 3.0 - 0.8 * np.sin((time[valley2_mask] - 800) * np.pi / 60)
    
    # 基准曲线
    baseline = 4.0 * np.ones_like(time)
    
    # 累积产氧量
    cumulative = np.cumsum(flow * 0.5 / 60)  # 0.5秒采样
    
    # 检测波谷
    valleys = analyzer.detect_valleys(time, flow, baseline, cumulative)
    
    # 打印结果
    print("检测到的波谷:")
    for i, valley in enumerate(valleys, 1):
        print(f"\n波谷 {i}:")
        print(f"  时间: {valley['center_time']}秒")
        print(f"  深度: {valley['depth']} L/min")
        print(f"  产氧损失: {valley['oxygen_loss']} L")
        print(f"  形态: {valley['shape']['type']}")