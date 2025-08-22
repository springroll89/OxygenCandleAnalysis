#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DOE实验设计模块
用于优化实验设计和响应面分析
"""

import numpy as np
import pandas as pd
from pyDOE2 import fullfact, fracfact, ccdesign, bbdesign, lhs
from scipy.optimize import minimize
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

class DOEDesigner:
    """DOE实验设计器"""
    
    def __init__(self):
        """初始化DOE设计器"""
        # 默认因子范围（基于氧烛产品特性）
        self.default_factors = {
            'A层重量(g)': {'low': 5, 'high': 10, 'center': 7},
            'B层重量(g)': {'low': 15, 'high': 25, 'center': 20},
            'C层总重(g)': {'low': 340, 'high': 380, 'center': 360},
            '压制压力(MPa)': {'low': 150, 'high': 250, 'center': 200},
            '混料时间(min)': {'low': 10, 'high': 30, 'center': 20},
            '氯酸钠含量(%)': {'low': 70, 'high': 85, 'center': 77.5}
        }
        
        # AS9100D要求的实验设计原则
        self.design_principles = {
            'min_runs': 8,  # 最少实验次数
            'center_points': 3,  # 中心点重复次数
            'alpha': 1.682,  # 星点距离（可旋转设计）
            'confidence_level': 0.95  # 置信水平
        }
        
    def generate_factorial_design(self, factors, levels=2, fraction=None):
        """
        生成全因子或部分因子设计
        
        Parameters:
        factors: dict，因子及其水平
        levels: int，水平数（2或3）
        fraction: str，部分因子生成元（如 'a b c abc'）
        
        Returns:
        DataFrame: 实验设计表
        """
        factor_names = list(factors.keys())
        n_factors = len(factor_names)
        
        if fraction:
            # 部分因子设计
            design_matrix = fracfact(fraction)
        else:
            # 全因子设计
            if levels == 2:
                design_matrix = fullfact([2] * n_factors)
                # 转换为-1, 1编码
                design_matrix = 2 * design_matrix - 1
            else:
                design_matrix = fullfact([levels] * n_factors)
                # 转换为-1, 0, 1编码
                design_matrix = design_matrix - (levels - 1) / 2
        
        # 转换为实际值
        experiments = pd.DataFrame()
        for i, factor_name in enumerate(factor_names):
            factor_info = factors[factor_name]
            low = factor_info['low']
            high = factor_info['high']
            
            if levels == 2:
                # 2水平：-1对应low，1对应high
                actual_values = low + (design_matrix[:, i] + 1) / 2 * (high - low)
            else:
                # 3水平：包括中心点
                center = factor_info.get('center', (low + high) / 2)
                actual_values = np.where(
                    design_matrix[:, i] == -1, low,
                    np.where(design_matrix[:, i] == 0, center, high)
                )
            
            experiments[factor_name] = actual_values
        
        # 添加实验序号
        experiments.insert(0, '实验序号', range(1, len(experiments) + 1))
        
        # 随机化实验顺序
        experiments['运行顺序'] = np.random.permutation(len(experiments)) + 1
        
        return experiments
    
    def generate_response_surface_design(self, factors, design_type='ccd'):
        """
        生成响应面设计
        
        Parameters:
        factors: dict，因子及其水平
        design_type: str，设计类型（'ccd'=中心复合设计，'bb'=Box-Behnken设计）
        
        Returns:
        DataFrame: 实验设计表
        """
        factor_names = list(factors.keys())
        n_factors = len(factor_names)
        
        if design_type == 'ccd':
            # 中心复合设计
            design_matrix = ccdesign(
                n_factors, 
                center=(2, 2),  # 2个中心点，重复2次
                alpha='r',  # 可旋转设计
                face='ccf'  # 面心设计
            )
        elif design_type == 'bb':
            # Box-Behnken设计
            design_matrix = bbdesign(n_factors, center=3)
        else:
            raise ValueError(f"Unknown design type: {design_type}")
        
        # 转换为实际值
        experiments = pd.DataFrame()
        for i, factor_name in enumerate(factor_names):
            factor_info = factors[factor_name]
            low = factor_info['low']
            high = factor_info['high']
            center = factor_info.get('center', (low + high) / 2)
            
            # 编码值转实际值
            coded = design_matrix[:, i]
            actual = center + coded * (high - low) / 2
            experiments[factor_name] = actual
        
        # 添加实验序号和运行顺序
        experiments.insert(0, '实验序号', range(1, len(experiments) + 1))
        experiments['运行顺序'] = np.random.permutation(len(experiments)) + 1
        
        # 标记设计点类型
        experiments['设计点类型'] = self._classify_design_points(design_matrix)
        
        return experiments
    
    def generate_optimal_design(self, factors, n_runs, criterion='D'):
        """
        生成最优设计（使用拉丁超立方设计）
        
        Parameters:
        factors: dict，因子及其水平
        n_runs: int，实验次数
        criterion: str，优化准则（'D'=D-optimal, 'I'=I-optimal）
        
        Returns:
        DataFrame: 实验设计表
        """
        factor_names = list(factors.keys())
        n_factors = len(factor_names)
        
        # 生成拉丁超立方设计
        lhs_design = lhs(n_factors, samples=n_runs, criterion=criterion.lower())
        
        # 转换为实际值
        experiments = pd.DataFrame()
        for i, factor_name in enumerate(factor_names):
            factor_info = factors[factor_name]
            low = factor_info['low']
            high = factor_info['high']
            
            # LHS设计值在[0,1]范围内，转换为实际值
            actual_values = low + lhs_design[:, i] * (high - low)
            experiments[factor_name] = actual_values
        
        # 添加实验序号
        experiments.insert(0, '实验序号', range(1, len(experiments) + 1))
        experiments['运行顺序'] = np.random.permutation(len(experiments)) + 1
        
        return experiments
    
    def analyze_factorial_effects(self, design_df, response):
        """
        分析因子效应
        
        Parameters:
        design_df: DataFrame，实验设计
        response: array-like，响应值
        
        Returns:
        dict: 效应分析结果
        """
        # 提取因子列（排除序号等）
        factor_cols = [col for col in design_df.columns 
                      if col not in ['实验序号', '运行顺序', '设计点类型']]
        
        X = design_df[factor_cols].values
        y = np.array(response)
        
        # 标准化因子（转为-1到1）
        X_scaled = np.zeros_like(X)
        for i in range(X.shape[1]):
            X_scaled[:, i] = 2 * (X[:, i] - X[:, i].min()) / (X[:, i].max() - X[:, i].min()) - 1
        
        # 主效应分析
        main_effects = {}
        for i, factor in enumerate(factor_cols):
            # 计算高低水平的平均响应差
            high_level = y[X_scaled[:, i] > 0].mean() if np.any(X_scaled[:, i] > 0) else 0
            low_level = y[X_scaled[:, i] < 0].mean() if np.any(X_scaled[:, i] < 0) else 0
            main_effects[factor] = high_level - low_level
        
        # 交互效应分析（二阶）
        interaction_effects = {}
        for i in range(len(factor_cols)):
            for j in range(i+1, len(factor_cols)):
                interaction = X_scaled[:, i] * X_scaled[:, j]
                high_inter = y[interaction > 0].mean() if np.any(interaction > 0) else 0
                low_inter = y[interaction < 0].mean() if np.any(interaction < 0) else 0
                interaction_name = f"{factor_cols[i]} × {factor_cols[j]}"
                interaction_effects[interaction_name] = high_inter - low_inter
        
        # 拟合线性模型
        poly = PolynomialFeatures(degree=2, include_bias=True)
        X_poly = poly.fit_transform(X_scaled)
        
        model = LinearRegression()
        model.fit(X_poly, y)
        
        # 计算R²和调整R²
        r2 = model.score(X_poly, y)
        n = len(y)
        p = X_poly.shape[1]
        adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1)
        
        # ANOVA分析
        y_pred = model.predict(X_poly)
        ss_total = np.sum((y - y.mean()) ** 2)
        ss_reg = np.sum((y_pred - y.mean()) ** 2)
        ss_res = np.sum((y - y_pred) ** 2)
        
        df_reg = p - 1
        df_res = n - p
        
        ms_reg = ss_reg / df_reg
        ms_res = ss_res / df_res
        
        f_stat = ms_reg / ms_res
        
        return {
            'main_effects': main_effects,
            'interaction_effects': interaction_effects,
            'model': model,
            'poly_features': poly,
            'R2': r2,
            'adjusted_R2': adj_r2,
            'ANOVA': {
                'SS_regression': ss_reg,
                'SS_residual': ss_res,
                'SS_total': ss_total,
                'F_statistic': f_stat,
                'df_regression': df_reg,
                'df_residual': df_res
            }
        }
    
    def fit_response_surface(self, design_df, response):
        """
        拟合响应面模型
        
        Parameters:
        design_df: DataFrame，实验设计
        response: array-like，响应值
        
        Returns:
        dict: 响应面模型
        """
        factor_cols = [col for col in design_df.columns 
                      if col not in ['实验序号', '运行顺序', '设计点类型']]
        
        X = design_df[factor_cols].values
        y = np.array(response)
        
        # 标准化
        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0)
        X_scaled = (X - X_mean) / X_std
        
        # 二次多项式
        poly = PolynomialFeatures(degree=2, include_bias=True)
        X_poly = poly.fit_transform(X_scaled)
        
        # 拟合模型
        model = LinearRegression()
        model.fit(X_poly, y)
        
        # 获取系数
        coefficients = model.coef_
        feature_names = poly.get_feature_names_out(factor_cols)
        
        # 解析系数
        coef_dict = {}
        for name, coef in zip(feature_names, coefficients):
            if name != '1':  # 跳过截距
                coef_dict[name] = coef
        
        return {
            'model': model,
            'poly_features': poly,
            'coefficients': coef_dict,
            'intercept': model.intercept_,
            'X_mean': X_mean,
            'X_std': X_std,
            'factor_names': factor_cols,
            'R2': model.score(X_poly, y)
        }
    
    def optimize_response(self, response_model, target='maximize', constraints=None):
        """
        优化响应
        
        Parameters:
        response_model: dict，响应面模型
        target: str或float，'maximize'、'minimize'或目标值
        constraints: dict，约束条件
        
        Returns:
        dict: 最优条件
        """
        model = response_model['model']
        poly = response_model['poly_features']
        X_mean = response_model['X_mean']
        X_std = response_model['X_std']
        factor_names = response_model['factor_names']
        
        # 定义目标函数
        def objective(x):
            x_scaled = (x - X_mean) / X_std
            x_poly = poly.transform(x_scaled.reshape(1, -1))
            pred = model.predict(x_poly)[0]
            
            if target == 'maximize':
                return -pred  # 最大化转为最小化
            elif target == 'minimize':
                return pred
            else:
                # 目标值
                return (pred - target) ** 2
        
        # 设置边界
        bounds = []
        for i, factor in enumerate(factor_names):
            if constraints and factor in constraints:
                bounds.append(constraints[factor])
            else:
                # 使用默认范围
                factor_range = self.default_factors.get(factor, {})
                bounds.append((
                    factor_range.get('low', X_mean[i] - 3*X_std[i]),
                    factor_range.get('high', X_mean[i] + 3*X_std[i])
                ))
        
        # 多起点优化
        best_result = None
        best_value = np.inf
        
        for _ in range(10):
            # 随机初始点
            x0 = np.array([np.random.uniform(b[0], b[1]) for b in bounds])
            
            # 优化
            result = minimize(objective, x0, bounds=bounds, method='L-BFGS-B')
            
            if result.fun < best_value:
                best_value = result.fun
                best_result = result
        
        # 计算最优响应
        x_opt = best_result.x
        x_scaled = (x_opt - X_mean) / X_std
        x_poly = poly.transform(x_scaled.reshape(1, -1))
        y_opt = model.predict(x_poly)[0]
        
        # 构建结果
        optimal_conditions = {}
        for factor, value in zip(factor_names, x_opt):
            optimal_conditions[factor] = round(value, 2)
        
        return {
            'optimal_conditions': optimal_conditions,
            'predicted_response': round(y_opt, 3),
            'optimization_target': target,
            'convergence': best_result.success,
            'message': best_result.message
        }
    
    def _classify_design_points(self, design_matrix):
        """分类设计点类型"""
        types = []
        for row in design_matrix:
            if np.all(np.abs(row) < 0.01):
                types.append('中心点')
            elif np.sum(np.abs(row) > 1.5) > 0:
                types.append('星点')
            elif np.all(np.abs(row) <= 1.01):
                types.append('因子点')
            else:
                types.append('其他')
        return types
    
    def generate_doe_report(self, design_df, analysis_results=None, output_path=None):
        """生成DOE报告"""
        report = []
        report.append("=" * 60)
        report.append("DOE实验设计报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        report.append(f"\n【实验设计】")
        report.append(f"实验总数: {len(design_df)}")
        
        factor_cols = [col for col in design_df.columns 
                      if col not in ['实验序号', '运行顺序', '设计点类型']]
        report.append(f"因子数: {len(factor_cols)}")
        report.append("因子列表:")
        for factor in factor_cols:
            report.append(f"  - {factor}: [{design_df[factor].min():.2f}, {design_df[factor].max():.2f}]")
        
        if '设计点类型' in design_df.columns:
            point_types = design_df['设计点类型'].value_counts()
            report.append("\n设计点分布:")
            for ptype, count in point_types.items():
                report.append(f"  {ptype}: {count}个")
        
        if analysis_results:
            report.append(f"\n【效应分析】")
            
            if 'main_effects' in analysis_results:
                report.append("\n主效应:")
                sorted_effects = sorted(analysis_results['main_effects'].items(), 
                                      key=lambda x: abs(x[1]), reverse=True)
                for factor, effect in sorted_effects:
                    report.append(f"  {factor}: {effect:+.3f}")
            
            if 'R2' in analysis_results:
                report.append(f"\n模型拟合:")
                report.append(f"  R²: {analysis_results['R2']:.4f}")
                if 'adjusted_R2' in analysis_results:
                    report.append(f"  调整R²: {analysis_results['adjusted_R2']:.4f}")
            
            if 'ANOVA' in analysis_results:
                anova = analysis_results['ANOVA']
                report.append(f"\n方差分析:")
                report.append(f"  F统计量: {anova['F_statistic']:.2f}")
                report.append(f"  回归平方和: {anova['SS_regression']:.2f}")
                report.append(f"  残差平方和: {anova['SS_residual']:.2f}")
        
        report.append("\n" + "=" * 60)
        report.append("AS9100D提示：请确保实验按随机顺序执行")
        
        report_text = '\n'.join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            
            # 同时保存设计表
            excel_path = output_path.replace('.txt', '.xlsx')
            design_df.to_excel(excel_path, index=False)
            print(f"DOE设计已保存: {excel_path}")
        
        return report_text