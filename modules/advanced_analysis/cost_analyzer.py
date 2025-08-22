#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成本效益分析模块
用于原料成本计算和性价比优化
"""

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize
import json
from datetime import datetime

class CostAnalyzer:
    """成本分析器"""
    
    def __init__(self, cost_data_file=None):
        """
        初始化成本分析器
        
        Parameters:
        cost_data_file: str，成本数据文件路径
        """
        # 默认原料成本（元/kg）
        self.material_costs = {
            '氯酸钠': 2800,
            '铁粉': 4500,
            '玻璃纤维': 8000,
            '二氧化锰': 12000,
            '氯化钡': 15000,
            '过氧化钡': 18000,
            '高锰酸钾': 9500,
            '硅藻土': 3200,
            '石棉纤维': 6500,
            '氧化镁': 4800,
            '氧化铝': 5500,
            '碳酸锂': 85000,
            '不锈钢纤维': 25000
        }
        
        # 工艺成本参数
        self.process_costs = {
            '混料': 50,  # 元/批次
            '压制': 80,  # 元/批次
            '组装': 30,  # 元/个
            '包装': 20,  # 元/个
            '质检': 100,  # 元/批次
            '人工': 200,  # 元/批次
            '能源': 150,  # 元/批次
            '设备折旧': 100  # 元/批次
        }
        
        # 质量成本参数（AS9100D要求）
        self.quality_costs = {
            '预防成本': {
                '培训': 5000,  # 元/月
                '工艺改进': 10000,  # 元/月
                '预防性维护': 8000  # 元/月
            },
            '评估成本': {
                '进料检验': 50,  # 元/批次
                '过程检验': 100,  # 元/批次
                '最终检验': 150,  # 元/批次
                '审核': 3000  # 元/月
            },
            '内部失败成本': {
                '返工': 500,  # 元/个
                '报废': 1000,  # 元/个
                '停工': 5000  # 元/小时
            },
            '外部失败成本': {
                '退货': 2000,  # 元/个
                '质保维修': 3000,  # 元/个
                '信誉损失': 10000  # 元/次
            }
        }
        
        # 如果提供了成本数据文件，加载数据
        if cost_data_file:
            self.load_cost_data(cost_data_file)
    
    def load_cost_data(self, filepath):
        """加载成本数据"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                cost_data = json.load(f)
                
                if 'material_costs' in cost_data:
                    self.material_costs.update(cost_data['material_costs'])
                if 'process_costs' in cost_data:
                    self.process_costs.update(cost_data['process_costs'])
                if 'quality_costs' in cost_data:
                    self.quality_costs.update(cost_data['quality_costs'])
                    
            print(f"✅ 成本数据已加载: {filepath}")
        except Exception as e:
            print(f"⚠️ 加载成本数据失败: {e}")
    
    def calculate_material_cost(self, formula):
        """
        计算原料成本
        
        Parameters:
        formula: dict，配方（成分：重量）
        
        Returns:
        dict: 成本明细
        """
        total_cost = 0
        cost_breakdown = {}
        
        for material, weight_g in formula.items():
            weight_kg = weight_g / 1000
            
            # 查找原料单价
            unit_cost = self.material_costs.get(material, 0)
            if unit_cost == 0:
                # 尝试模糊匹配
                for known_material, known_cost in self.material_costs.items():
                    if known_material in material or material in known_material:
                        unit_cost = known_cost
                        break
            
            material_cost = weight_kg * unit_cost
            cost_breakdown[material] = {
                'weight_g': weight_g,
                'unit_cost_per_kg': unit_cost,
                'cost': round(material_cost, 2)
            }
            total_cost += material_cost
        
        return {
            'total_material_cost': round(total_cost, 2),
            'breakdown': cost_breakdown,
            'total_weight_g': sum(formula.values())
        }
    
    def calculate_production_cost(self, batch_size=100):
        """
        计算生产成本
        
        Parameters:
        batch_size: int，批次大小（个数）
        
        Returns:
        dict: 生产成本明细
        """
        # 固定成本（按批次）
        fixed_costs = {
            '混料': self.process_costs['混料'],
            '质检': self.process_costs['质检'],
            '人工': self.process_costs['人工'],
            '能源': self.process_costs['能源'],
            '设备折旧': self.process_costs['设备折旧']
        }
        
        # 变动成本（按个数）
        variable_costs = {
            '压制': self.process_costs['压制'] * batch_size / 100,  # 假设100个一批压制
            '组装': self.process_costs['组装'] * batch_size,
            '包装': self.process_costs['包装'] * batch_size
        }
        
        total_fixed = sum(fixed_costs.values())
        total_variable = sum(variable_costs.values())
        total_production = total_fixed + total_variable
        
        # 单位生产成本
        unit_production_cost = total_production / batch_size
        
        return {
            'total_production_cost': round(total_production, 2),
            'unit_production_cost': round(unit_production_cost, 2),
            'fixed_costs': fixed_costs,
            'variable_costs': variable_costs,
            'batch_size': batch_size
        }
    
    def calculate_quality_cost(self, production_volume, defect_rate=0.02):
        """
        计算质量成本（基于AS9100D）
        
        Parameters:
        production_volume: int，月产量
        defect_rate: float，缺陷率
        
        Returns:
        dict: 质量成本明细
        """
        # 预防成本（月度）
        prevention = sum(self.quality_costs['预防成本'].values())
        
        # 评估成本
        batch_count = production_volume / 100  # 假设100个一批
        assessment = (
            self.quality_costs['评估成本']['进料检验'] * batch_count +
            self.quality_costs['评估成本']['过程检验'] * batch_count +
            self.quality_costs['评估成本']['最终检验'] * batch_count +
            self.quality_costs['评估成本']['审核']
        )
        
        # 失败成本
        defect_count = production_volume * defect_rate
        internal_failure = defect_count * 0.7 * self.quality_costs['内部失败成本']['返工']
        external_failure = defect_count * 0.3 * self.quality_costs['外部失败成本']['退货']
        
        total_quality_cost = prevention + assessment + internal_failure + external_failure
        unit_quality_cost = total_quality_cost / production_volume
        
        # COPQ (Cost of Poor Quality)
        copq = (internal_failure + external_failure) / (production_volume * 100) * 100  # 假设单价100元
        
        return {
            'total_quality_cost': round(total_quality_cost, 2),
            'unit_quality_cost': round(unit_quality_cost, 2),
            'prevention_cost': round(prevention, 2),
            'assessment_cost': round(assessment, 2),
            'internal_failure_cost': round(internal_failure, 2),
            'external_failure_cost': round(external_failure, 2),
            'COPQ_percentage': round(copq, 2),
            'defect_rate': defect_rate * 100
        }
    
    def calculate_total_cost(self, formula, batch_size=100, defect_rate=0.02):
        """
        计算总成本
        
        Parameters:
        formula: dict，配方
        batch_size: int，批次大小
        defect_rate: float，缺陷率
        
        Returns:
        dict: 总成本分析
        """
        # 原料成本
        material_result = self.calculate_material_cost(formula)
        
        # 生产成本
        production_result = self.calculate_production_cost(batch_size)
        
        # 质量成本
        quality_result = self.calculate_quality_cost(batch_size, defect_rate)
        
        # 单位总成本
        unit_total_cost = (
            material_result['total_material_cost'] +
            production_result['unit_production_cost'] +
            quality_result['unit_quality_cost']
        )
        
        # 良品成本（考虑缺陷率）
        good_product_cost = unit_total_cost / (1 - defect_rate)
        
        return {
            'unit_total_cost': round(unit_total_cost, 2),
            'good_product_cost': round(good_product_cost, 2),
            'material_cost': material_result,
            'production_cost': production_result,
            'quality_cost': quality_result,
            'cost_structure': {
                '原料成本占比': round(material_result['total_material_cost'] / unit_total_cost * 100, 1),
                '生产成本占比': round(production_result['unit_production_cost'] / unit_total_cost * 100, 1),
                '质量成本占比': round(quality_result['unit_quality_cost'] / unit_total_cost * 100, 1)
            }
        }
    
    def optimize_cost_performance(self, formulas_df, performance_df, 
                                 target_performance=85, max_cost=150):
        """
        优化成本性能比
        
        Parameters:
        formulas_df: DataFrame，配方数据
        performance_df: DataFrame，性能数据
        target_performance: float，目标性能得分
        max_cost: float，最大成本限制
        
        Returns:
        dict: 优化结果
        """
        results = []
        
        for idx, formula_row in formulas_df.iterrows():
            # 获取配方
            formula = formula_row.to_dict()
            
            # 计算成本
            cost_analysis = self.calculate_total_cost(formula)
            unit_cost = cost_analysis['unit_total_cost']
            
            # 获取性能
            if idx < len(performance_df):
                performance = performance_df.iloc[idx].get('综合得分', 0)
            else:
                performance = 0
            
            # 计算性价比
            if unit_cost > 0:
                cost_performance_ratio = performance / unit_cost
            else:
                cost_performance_ratio = 0
            
            # 检查约束
            meets_constraints = (
                performance >= target_performance and
                unit_cost <= max_cost
            )
            
            results.append({
                'formula_id': idx,
                'unit_cost': unit_cost,
                'performance': performance,
                'cost_performance_ratio': round(cost_performance_ratio, 3),
                'meets_constraints': meets_constraints
            })
        
        results_df = pd.DataFrame(results)
        
        # 找出最优方案
        valid_results = results_df[results_df['meets_constraints']]
        
        if not valid_results.empty:
            optimal_idx = valid_results['cost_performance_ratio'].idxmax()
            optimal = valid_results.loc[optimal_idx]
        else:
            # 如果没有满足约束的，选择性价比最高的
            optimal_idx = results_df['cost_performance_ratio'].idxmax()
            optimal = results_df.loc[optimal_idx]
        
        return {
            'optimal_formula': optimal.to_dict(),
            'all_results': results_df,
            'valid_count': len(valid_results),
            'total_count': len(results_df)
        }
    
    def perform_cost_breakdown_analysis(self, formula):
        """
        执行成本分解分析
        
        Parameters:
        formula: dict，配方
        
        Returns:
        dict: 成本分解分析
        """
        material_cost = self.calculate_material_cost(formula)
        
        # 按成本贡献排序
        sorted_materials = sorted(
            material_cost['breakdown'].items(),
            key=lambda x: x[1]['cost'],
            reverse=True
        )
        
        # 帕累托分析（80/20原则）
        total_cost = material_cost['total_material_cost']
        cumulative_cost = 0
        cumulative_percentage = 0
        pareto_materials = []
        
        for material, info in sorted_materials:
            cumulative_cost += info['cost']
            cumulative_percentage = cumulative_cost / total_cost * 100
            
            pareto_materials.append({
                'material': material,
                'cost': info['cost'],
                'percentage': info['cost'] / total_cost * 100,
                'cumulative_percentage': cumulative_percentage
            })
            
            if cumulative_percentage >= 80:
                break
        
        # ABC分类
        abc_classification = []
        cumulative = 0
        
        for material, info in sorted_materials:
            percentage = info['cost'] / total_cost * 100
            cumulative += percentage
            
            if cumulative <= 70:
                category = 'A'
            elif cumulative <= 90:
                category = 'B'
            else:
                category = 'C'
            
            abc_classification.append({
                'material': material,
                'category': category,
                'cost': info['cost'],
                'percentage': percentage
            })
        
        return {
            'total_cost': total_cost,
            'pareto_analysis': pareto_materials,
            'abc_classification': abc_classification,
            'cost_drivers': pareto_materials[:3] if len(pareto_materials) >= 3 else pareto_materials
        }
    
    def calculate_roi(self, investment, annual_savings, years=5, discount_rate=0.1):
        """
        计算投资回报率
        
        Parameters:
        investment: float，初始投资
        annual_savings: float，年度节省
        years: int，年数
        discount_rate: float，贴现率
        
        Returns:
        dict: ROI分析
        """
        # 简单回收期
        payback_period = investment / annual_savings if annual_savings > 0 else float('inf')
        
        # NPV（净现值）
        npv = -investment
        for year in range(1, years + 1):
            npv += annual_savings / ((1 + discount_rate) ** year)
        
        # IRR（内部收益率）- 简化计算
        irr = None
        if annual_savings > 0:
            # 使用二分法近似计算IRR
            low_rate = 0
            high_rate = 1
            
            for _ in range(50):
                mid_rate = (low_rate + high_rate) / 2
                test_npv = -investment
                
                for year in range(1, years + 1):
                    test_npv += annual_savings / ((1 + mid_rate) ** year)
                
                if abs(test_npv) < 0.01:
                    irr = mid_rate
                    break
                elif test_npv > 0:
                    low_rate = mid_rate
                else:
                    high_rate = mid_rate
        
        # ROI
        total_return = annual_savings * years
        roi = (total_return - investment) / investment * 100 if investment > 0 else 0
        
        return {
            'payback_period_years': round(payback_period, 2),
            'NPV': round(npv, 2),
            'IRR': round(irr * 100, 2) if irr else None,
            'ROI_percentage': round(roi, 2),
            'break_even_year': int(np.ceil(payback_period)) if payback_period < float('inf') else None
        }
    
    def generate_cost_report(self, cost_analysis, output_path=None):
        """生成成本分析报告"""
        report = []
        report.append("=" * 60)
        report.append("成本效益分析报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if 'unit_total_cost' in cost_analysis:
            report.append(f"\n【成本汇总】")
            report.append(f"单位总成本: ¥{cost_analysis['unit_total_cost']}")
            report.append(f"良品成本: ¥{cost_analysis['good_product_cost']}")
            
            report.append(f"\n【成本结构】")
            for item, percentage in cost_analysis['cost_structure'].items():
                report.append(f"  {item}: {percentage}%")
        
        if 'material_cost' in cost_analysis:
            material = cost_analysis['material_cost']
            report.append(f"\n【原料成本明细】")
            report.append(f"总原料成本: ¥{material['total_material_cost']}")
            report.append(f"总重量: {material['total_weight_g']}g")
            
            # 主要原料（前5个）
            sorted_materials = sorted(
                material['breakdown'].items(),
                key=lambda x: x[1]['cost'],
                reverse=True
            )[:5]
            
            report.append("\n主要原料成本:")
            for mat, info in sorted_materials:
                report.append(f"  {mat}: ¥{info['cost']} ({info['weight_g']}g)")
        
        if 'quality_cost' in cost_analysis:
            quality = cost_analysis['quality_cost']
            report.append(f"\n【质量成本】")
            report.append(f"总质量成本: ¥{quality['total_quality_cost']}")
            report.append(f"COPQ: {quality['COPQ_percentage']}%")
            report.append(f"缺陷率: {quality['defect_rate']}%")
        
        report.append("\n" + "=" * 60)
        report.append("AS9100D提示：质量成本应持续监控和改进")
        
        report_text = '\n'.join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text