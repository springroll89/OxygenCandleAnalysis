#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器学习预测模块 - 修正版
优化真正的可控参数（配方成分、工艺参数）而非结果参数
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, RBF, ConstantKernel
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import joblib
import json
from datetime import datetime
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class MLPredictor:
    """机器学习预测器 - 配方优化版"""
    
    def __init__(self, model_type='random_forest'):
        """
        初始化预测器
        
        Parameters:
        model_type: 模型类型 ('random_forest', 'gradient_boost', 'gaussian_process')
        """
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_importance = None
        self.is_trained = False
        
        # AS9100D要求的预测精度
        self.min_r2 = 0.85
        self.max_mae_percent = 5  # 最大平均绝对误差百分比
        
        # 配方-性能映射模型（简化版）
        self.performance_predictor = None
        
    def prepare_features(self, data):
        """
        准备特征工程
        
        Parameters:
        data: DataFrame，原始数据
        
        Returns:
        DataFrame: 特征矩阵
        """
        features = pd.DataFrame()
        
        # 基础特征
        if '启动时长(秒)' in data.columns:
            features['startup_time'] = data['启动时长(秒)']
            features['startup_speed'] = 1 / (data['启动时长(秒)'] + 0.1)  # 启动速度
        
        if '达峰时长(秒)' in data.columns:
            features['peak_time'] = data['达峰时长(秒)']
            if 'startup_time' in features.columns:
                features['peak_efficiency'] = features['startup_time'] / (data['达峰时长(秒)'] + 0.1)
        
        if '产氧时间(分钟)' in data.columns:
            features['duration_min'] = data['产氧时间(分钟)']
            features['duration_squared'] = data['产氧时间(分钟)'] ** 2
        
        if '累计流量(升)' in data.columns:
            features['total_oxygen'] = data['累计流量(升)']
            if '产氧时间(分钟)' in data.columns:
                features['avg_flow_rate'] = data['累计流量(升)'] / (data['产氧时间(分钟)'] + 0.1)
        
        if '外壳最高温度(°C)' in data.columns:
            features['shell_temp'] = data['外壳最高温度(°C)']
            features['temp_safety_margin'] = 230 - data['外壳最高温度(°C)']  # 距离限值的裕度
        
        if '异常次数' in data.columns:
            features['anomaly_count'] = data['异常次数']
            features['has_anomaly'] = (data['异常次数'] > 0).astype(int)
        
        if '异常持续时间(秒)' in data.columns:
            features['anomaly_duration'] = data['异常持续时间(秒)']
            if '产氧时间(分钟)' in data.columns:
                features['anomaly_rate'] = data['异常持续时间(秒)'] / (data['产氧时间(分钟)'] * 60 + 1)
        
        # 温度等级编码
        if '温度等级' in data.columns:
            temp_mapping = {'低温': 0, '常温': 1, '高温': 2, '未注明': -1}
            features['temp_level'] = data['温度等级'].map(temp_mapping).fillna(-1)
        
        # 配方特征（如果有）
        if '样品编号' in data.columns:
            # 提取数字部分作为配方代号
            features['formula_code'] = data['样品编号'].str.extract(r'(\d+)')[0].astype(float).fillna(0)
        
        # 交互特征
        if 'startup_time' in features.columns and 'shell_temp' in features.columns:
            features['startup_temp_interaction'] = features['startup_time'] * features['shell_temp']
        
        if 'duration_min' in features.columns and 'anomaly_count' in features.columns:
            features['duration_anomaly_interaction'] = features['duration_min'] * features['anomaly_count']
        
        # 确保所有特征都存在（添加默认值）
        default_features = {
            'startup_time': 1.0,
            'startup_speed': 1.0,
            'peak_time': 5.0,
            'peak_efficiency': 0.2,
            'duration_min': 25.0,
            'duration_squared': 625.0,
            'total_oxygen': 100.0,
            'avg_flow_rate': 4.0,
            'shell_temp': 180.0,
            'temp_safety_margin': 50.0,
            'anomaly_count': 0,
            'has_anomaly': 0,
            'anomaly_duration': 0,
            'anomaly_rate': 0,
            'temp_level': 1,
            'formula_code': 0,
            'startup_temp_interaction': 180.0,
            'duration_anomaly_interaction': 0
        }
        
        for feature, default_value in default_features.items():
            if feature not in features.columns:
                features[feature] = default_value
        
        return features
    
    def train(self, train_data, target_column='综合得分'):
        """
        训练预测模型
        
        Parameters:
        train_data: DataFrame，训练数据
        target_column: str，目标变量列名
        
        Returns:
        dict: 训练结果
        """
        # 准备特征
        X = self.prepare_features(train_data)
        y = train_data[target_column].values
        
        # 移除包含NaN的样本
        valid_idx = ~(X.isna().any(axis=1) | pd.isna(y))
        X = X[valid_idx]
        y = y[valid_idx]
        
        if len(X) < 10:
            return {
                'status': 'FAIL',
                'message': f'训练样本太少（{len(X)}个），至少需要10个'
            }
        
        # 标准化
        X_scaled = self.scaler.fit_transform(X)
        
        # 保存特征名
        self.scaler.feature_names_in_ = X.columns.tolist()
        
        # 选择模型
        if self.model_type == 'random_forest':
            self.model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=2,
                min_samples_leaf=1,
                random_state=42
            )
        elif self.model_type == 'gradient_boost':
            self.model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
        elif self.model_type == 'gaussian_process':
            kernel = ConstantKernel(1.0) * Matern(length_scale=1.0, nu=1.5)
            self.model = GaussianProcessRegressor(
                kernel=kernel,
                alpha=1e-6,
                normalize_y=True,
                random_state=42
            )
        
        # 训练模型
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        # 交叉验证
        cv_scores = cross_val_score(
            self.model, X_scaled, y, 
            cv=min(5, len(X)//2), 
            scoring='r2'
        )
        
        # 训练集性能
        y_pred = self.model.predict(X_scaled)
        train_r2 = r2_score(y, y_pred)
        train_mae = mean_absolute_error(y, y_pred)
        train_rmse = np.sqrt(mean_squared_error(y, y_pred))
        
        # 特征重要性
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = pd.DataFrame({
                'feature': X.columns,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
        
        # 检查AS9100D合规性
        compliance = self.check_model_compliance(train_r2, train_mae, y)
        
        return {
            'status': 'SUCCESS',
            'model_type': self.model_type,
            'n_samples': len(X),
            'n_features': X.shape[1],
            'train_r2': round(train_r2, 4),
            'train_mae': round(train_mae, 4),
            'train_rmse': round(train_rmse, 4),
            'cv_r2_mean': round(cv_scores.mean(), 4),
            'cv_r2_std': round(cv_scores.std(), 4),
            'feature_importance': self.feature_importance,
            'AS9100D_compliance': compliance
        }
    
    def predict(self, test_data, return_uncertainty=False):
        """
        预测新样本
        
        Parameters:
        test_data: DataFrame，测试数据
        return_uncertainty: bool，是否返回不确定性估计
        
        Returns:
        dict: 预测结果
        """
        if not self.is_trained:
            return {'status': 'ERROR', 'message': '模型未训练'}
        
        # 准备特征
        X = self.prepare_features(test_data)
        
        # 确保特征顺序一致
        if hasattr(self.scaler, 'feature_names_in_'):
            X = X[self.scaler.feature_names_in_]
        
        X_scaled = self.scaler.transform(X)
        
        # 预测
        predictions = self.model.predict(X_scaled)
        
        results = {
            'status': 'SUCCESS',
            'predictions': predictions,
            'sample_ids': test_data.get('样品编号', range(len(test_data))).tolist()
        }
        
        # 不确定性估计（如果支持）
        if return_uncertainty:
            if self.model_type == 'gaussian_process':
                _, std = self.model.predict(X_scaled, return_std=True)
                results['uncertainty'] = std
                results['confidence_lower'] = predictions - 1.96 * std
                results['confidence_upper'] = predictions + 1.96 * std
            elif self.model_type == 'random_forest':
                # 使用树的预测分布估计不确定性
                tree_predictions = np.array([
                    tree.predict(X_scaled) for tree in self.model.estimators_
                ])
                results['uncertainty'] = tree_predictions.std(axis=0)
                results['confidence_lower'] = np.percentile(tree_predictions, 2.5, axis=0)
                results['confidence_upper'] = np.percentile(tree_predictions, 97.5, axis=0)
        
        return results
    
    def optimize_formula(self, target_score=90, n_suggestions=5):
        """
        基于优化推荐配方（优化真正的可控参数）
        
        Parameters:
        target_score: float，目标得分
        n_suggestions: int，推荐数量
        
        Returns:
        dict: 配方优化建议
        """
        if not self.is_trained:
            return {'status': 'ERROR', 'message': '模型未训练'}
        
        # 定义真正可控的参数搜索空间
        controllable_params = {
            # A层配方参数
            'A层氯酸钠比例': (70, 85),      # %
            'A层铁粉比例': (10, 20),        # %
            'A层玻璃纤维比例': (5, 15),     # %
            'A层重量': (5, 10),             # g
            
            # B层配方参数
            'B层过氧化钡比例': (60, 80),    # %
            'B层二氧化锰比例': (5, 15),     # %
            'B层重量': (15, 25),            # g
            
            # C层配方参数
            'C层氯酸钠比例': (75, 85),      # %
            'C层铁粉比例': (8, 15),         # %
            'C层硅藻土比例': (5, 10),       # %
            'C层总重': (340, 380),          # g
            
            # 工艺参数
            '压制压力': (150, 250),         # MPa
            '混料时间': (10, 30),           # 分钟
            '压制温度': (20, 40),           # °C
            '原料粒度': (100, 300),         # 目
        }
        
        # 生成候选配方
        n_candidates = 1000
        candidates_formulas = []  # 存储原始配方参数
        candidates_features = []  # 存储转换后的特征
        
        for _ in range(n_candidates):
            candidate_formula = {}
            
            # 生成配方参数
            for param, (low, high) in controllable_params.items():
                candidate_formula[param] = np.random.uniform(low, high)
            
            # 确保每层成分比例和为100%（归一化处理）
            # A层归一化
            a_total = (candidate_formula['A层氯酸钠比例'] + 
                      candidate_formula['A层铁粉比例'] + 
                      candidate_formula['A层玻璃纤维比例'])
            candidate_formula['A层氯酸钠比例'] = (candidate_formula['A层氯酸钠比例'] / a_total) * 100
            candidate_formula['A层铁粉比例'] = (candidate_formula['A层铁粉比例'] / a_total) * 100
            candidate_formula['A层玻璃纤维比例'] = (candidate_formula['A层玻璃纤维比例'] / a_total) * 100
            
            # B层归一化（剩余部分为其他添加剂）
            b_total = candidate_formula['B层过氧化钡比例'] + candidate_formula['B层二氧化锰比例']
            if b_total > 92:  # 确保至少有8%的其他成分
                factor = 92 / b_total
                candidate_formula['B层过氧化钡比例'] *= factor
                candidate_formula['B层二氧化锰比例'] *= factor
            
            # C层归一化
            c_total = (candidate_formula['C层氯酸钠比例'] + 
                      candidate_formula['C层铁粉比例'] + 
                      candidate_formula['C层硅藻土比例'])
            if c_total > 92:
                factor = 92 / c_total
                candidate_formula['C层氯酸钠比例'] *= factor
                candidate_formula['C层铁粉比例'] *= factor
                candidate_formula['C层硅藻土比例'] *= factor
            
            # 保存原始配方
            candidates_formulas.append(candidate_formula)
            
            # 基于配方参数预测可能的性能指标
            predicted_performance = self.predict_performance_from_formula(candidate_formula)
            
            # 转换为模型需要的特征格式
            features = self.formula_to_features(candidate_formula, predicted_performance)
            candidates_features.append(features)
        
        # 转换为DataFrame
        candidates_df = pd.DataFrame(candidates_features)
        
        # 确保特征顺序一致
        if hasattr(self.scaler, 'feature_names_in_'):
            required_features = self.scaler.feature_names_in_
            for feat in required_features:
                if feat not in candidates_df.columns:
                    candidates_df[feat] = 0
            candidates_df = candidates_df[required_features]
        
        # 预测得分
        try:
            X_candidates = self.scaler.transform(candidates_df)
            predictions = self.model.predict(X_candidates)
        except Exception as e:
            return {'status': 'ERROR', 'message': f'预测失败: {str(e)}'}
        
        # 选择最佳配方
        best_indices = np.argsort(predictions)[-n_suggestions:][::-1]
        
        suggestions = []
        for rank, idx in enumerate(best_indices, 1):
            original_formula = candidates_formulas[idx]
            predicted_perf = self.predict_performance_from_formula(original_formula)
            
            suggestion = {
                'predicted_score': round(float(predictions[idx]), 2),
                'ranking': rank,
                'formula': {
                    'A层_点火层': {
                        '重量': f"{original_formula['A层重量']:.1f}g",
                        '成分': {
                            '氯酸钠': f"{original_formula['A层氯酸钠比例']:.1f}%",
                            '铁粉': f"{original_formula['A层铁粉比例']:.1f}%",
                            '玻璃纤维': f"{original_formula['A层玻璃纤维比例']:.1f}%"
                        }
                    },
                    'B层_引燃层': {
                        '重量': f"{original_formula['B层重量']:.1f}g",
                        '成分': {
                            '过氧化钡': f"{original_formula['B层过氧化钡比例']:.1f}%",
                            '二氧化锰': f"{original_formula['B层二氧化锰比例']:.1f}%",
                            '其他添加剂': f"{100 - original_formula['B层过氧化钡比例'] - original_formula['B层二氧化锰比例']:.1f}%"
                        }
                    },
                    'C层_主体层': {
                        '重量': f"{original_formula['C层总重']:.1f}g",
                        '成分': {
                            '氯酸钠': f"{original_formula['C层氯酸钠比例']:.1f}%",
                            '铁粉': f"{original_formula['C层铁粉比例']:.1f}%",
                            '硅藻土': f"{original_formula['C层硅藻土比例']:.1f}%",
                            '其他成分': f"{100 - original_formula['C层氯酸钠比例'] - original_formula['C层铁粉比例'] - original_formula['C层硅藻土比例']:.1f}%"
                        }
                    }
                },
                'process_params': {
                    '压制压力': f"{original_formula['压制压力']:.0f} MPa",
                    '混料时间': f"{original_formula['混料时间']:.0f} 分钟",
                    '压制温度': f"{original_formula['压制温度']:.0f} °C",
                    '原料粒度': f"{original_formula['原料粒度']:.0f} 目"
                },
                'expected_performance': {
                    '预计启动时长': f"{predicted_perf.get('启动时长', 1.5):.1f} 秒",
                    '预计达峰时长': f"{predicted_perf.get('达峰时长', 8.0):.1f} 秒",
                    '预计产氧时间': f"{predicted_perf.get('产氧时间', 25.0):.1f} 分钟",
                    '预计外壳温度': f"{predicted_perf.get('外壳温度', 185.0):.0f} °C",
                    '预计异常概率': f"{predicted_perf.get('异常概率', 5.0):.1f}%"
                },
                'optimization_notes': self.generate_optimization_notes(original_formula, predicted_perf)
            }
            
            suggestions.append(suggestion)
        
        return {
            'status': 'SUCCESS',
            'target_score': target_score,
            'suggestions': suggestions,
            'optimization_method': 'Formula-Based Optimization',
            'note': '建议配方基于历史数据预测，实际效果需要实验验证',
            'AS9100D_reminder': '请按照AS9100D标准进行配方变更控制和验证'
        }
    
    def predict_performance_from_formula(self, formula_params):
        """
        基于配方参数预测性能指标
        使用经验公式或简化模型
        
        Parameters:
        formula_params: dict，配方参数
        
        Returns:
        dict: 预测的性能指标
        """
        predicted = {}
        
        # 启动时长主要受A层（点火层）影响
        # A层重量越大、铁粉含量越高，启动越快
        predicted['启动时长'] = max(0.5, 
            5.0 - formula_params['A层重量'] * 0.3 - 
            formula_params['A层铁粉比例'] * 0.05)
        
        # 达峰时长受A层和B层影响
        predicted['达峰时长'] = max(3.0,
            15.0 - formula_params['B层重量'] * 0.2 - 
            formula_params['B层过氧化钡比例'] * 0.05)
        
        # 产氧时间主要受C层总重和成分影响
        predicted['产氧时间'] = (
            formula_params['C层总重'] * 0.065 +  # 基础时间
            formula_params['C层氯酸钠比例'] * 0.05 -  # 氯酸钠越多，时间越长
            formula_params['C层铁粉比例'] * 0.1  # 铁粉越多，反应越快，时间越短
        )
        
        # 外壳温度受整体铁粉含量和压制压力影响
        avg_iron_content = (
            formula_params['A层铁粉比例'] * formula_params['A层重量'] * 0.01 +
            formula_params['C层铁粉比例'] * formula_params['C层总重'] * 0.01
        ) / (formula_params['A层重量'] + formula_params['B层重量'] + formula_params['C层总重'])
        
        predicted['外壳温度'] = (
            150 + avg_iron_content * 500 +  # 铁粉影响
            formula_params['压制压力'] * 0.05  # 压制压力影响
        )
        
        # 异常概率受工艺参数影响
        predicted['异常概率'] = max(0, min(100,
            20 - formula_params['混料时间'] * 0.3 -  # 混料时间越长，异常越少
            (200 - abs(formula_params['压制压力'] - 200)) * 0.05  # 压力偏离最优值，异常增加
        ))
        
        return predicted
    
    def formula_to_features(self, formula_params, predicted_performance):
        """
        将配方参数转换为模型需要的特征
        
        Parameters:
        formula_params: dict，配方参数
        predicted_performance: dict，预测的性能
        
        Returns:
        dict: 特征字典
        """
        features = {
            # 使用预测的性能作为特征
            'startup_time': predicted_performance.get('启动时长', 2.0),
            'peak_time': predicted_performance.get('达峰时长', 8.0),
            'duration_min': predicted_performance.get('产氧时间', 25.0),
            'shell_temp': predicted_performance.get('外壳温度', 185.0),
            
            # 计算其他必要的特征
            'startup_speed': 1 / (predicted_performance.get('启动时长', 2.0) + 0.1),
            'peak_efficiency': predicted_performance.get('启动时长', 2.0) / (predicted_performance.get('达峰时长', 8.0) + 0.1),
            'duration_squared': predicted_performance.get('产氧时间', 25.0) ** 2,
            'temp_safety_margin': 230 - predicted_performance.get('外壳温度', 185.0),
            
            # 异常相关特征
            'anomaly_count': int(predicted_performance.get('异常概率', 5.0) > 10),  # 简化：概率>10%则可能有异常
            'has_anomaly': int(predicted_performance.get('异常概率', 5.0) > 10),
            'anomaly_duration': predicted_performance.get('异常概率', 5.0) * 2,  # 简化估算
            'anomaly_rate': predicted_performance.get('异常概率', 5.0) / 100,
            
            # 其他特征
            'total_oxygen': predicted_performance.get('产氧时间', 25.0) * 4.5,  # 假设平均流量4.5L/min
            'avg_flow_rate': 4.5,
            'temp_level': 1,  # 常温
            'formula_code': np.random.randint(100, 999),  # 随机配方代码
            
            # 交互特征
            'startup_temp_interaction': predicted_performance.get('启动时长', 2.0) * predicted_performance.get('外壳温度', 185.0),
            'duration_anomaly_interaction': predicted_performance.get('产氧时间', 25.0) * int(predicted_performance.get('异常概率', 5.0) > 10)
        }
        
        return features
    
    def generate_optimization_notes(self, formula, performance):
        """
        生成配方优化说明
        
        Parameters:
        formula: dict，配方参数
        performance: dict，预测性能
        
        Returns:
        list: 优化说明列表
        """
        notes = []
        
        # 分析A层
        if formula['A层重量'] < 7:
            notes.append("A层重量偏低，可能影响点火可靠性")
        elif formula['A层重量'] > 9:
            notes.append("A层重量偏高，可能延长启动时间")
        
        if formula['A层铁粉比例'] > 18:
            notes.append("A层铁粉含量较高，注意控制初始温升")
        
        # 分析C层
        if formula['C层氯酸钠比例'] < 78:
            notes.append("C层氯酸钠含量偏低，可能影响产氧量")
        elif formula['C层氯酸钠比例'] > 83:
            notes.append("C层氯酸钠含量较高，注意控制反应速率")
        
        # 分析工艺参数
        if formula['压制压力'] < 180:
            notes.append("压制压力偏低，可能影响产品密度和强度")
        elif formula['压制压力'] > 220:
            notes.append("压制压力偏高，注意防止过度压实")
        
        if formula['混料时间'] < 15:
            notes.append("混料时间较短，确保混合均匀性")
        
        # 分析预测性能
        if performance.get('外壳温度', 185) > 210:
            notes.append("预计外壳温度较高，建议增加隔热措施")
        
        if performance.get('异常概率', 5) > 10:
            notes.append("异常风险较高，建议优化工艺参数")
        
        if not notes:
            notes.append("配方参数均衡，预期性能良好")
        
        return notes
    
    def check_model_compliance(self, r2, mae, y_true):
        """检查模型是否符合AS9100D标准"""
        compliance = {
            'status': 'PASS',
            'checks': []
        }
        
        # R²检查
        if r2 < self.min_r2:
            compliance['status'] = 'FAIL'
            compliance['checks'].append(f'R² = {r2:.3f} < {self.min_r2} (最小要求)')
        else:
            compliance['checks'].append(f'R² = {r2:.3f} ✓')
        
        # MAE百分比检查
        mae_percent = (mae / np.mean(y_true)) * 100
        if mae_percent > self.max_mae_percent:
            compliance['status'] = 'WARNING'
            compliance['checks'].append(f'MAE% = {mae_percent:.1f}% > {self.max_mae_percent}% (建议值)')
        else:
            compliance['checks'].append(f'MAE% = {mae_percent:.1f}% ✓')
        
        return compliance
    
    def save_model(self, filepath):
        """保存模型"""
        if not self.is_trained:
            return False
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'model_type': self.model_type,
            'feature_importance': self.feature_importance,
            'feature_names': self.scaler.feature_names_in_ if hasattr(self.scaler, 'feature_names_in_') else None,
            'timestamp': datetime.now().isoformat()
        }
        
        joblib.dump(model_data, filepath)
        return True
    
    def load_model(self, filepath):
        """加载模型"""
        model_data = joblib.load(filepath)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.model_type = model_data['model_type']
        self.feature_importance = model_data.get('feature_importance')
        
        # 恢复特征名
        if 'feature_names' in model_data and model_data['feature_names']:
            self.scaler.feature_names_in_ = model_data['feature_names']
        
        self.is_trained = True
        
        return True
    
    def generate_prediction_report(self, results, output_path=None):
        """生成预测报告"""
        report = []
        report.append("=" * 60)
        report.append("机器学习配方优化报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"模型类型: {self.model_type}")
        
        if 'suggestions' in results:
            report.append(f"\n目标得分: {results.get('target_score', 90)}")
            report.append(f"优化方法: {results.get('optimization_method', 'Formula-Based')}")
            report.append("\n" + "=" * 60)
            
            for suggestion in results['suggestions']:
                report.append(f"\n【方案{suggestion['ranking']}】预测得分: {suggestion['predicted_score']}")
                report.append("-" * 40)
                
                # 配方详情
                formula = suggestion['formula']
                report.append("\n配方组成:")
                
                # A层
                report.append(f"\nA层（点火层）- {formula['A层_点火层']['重量']}")
                for comp, value in formula['A层_点火层']['成分'].items():
                    report.append(f"  • {comp}: {value}")
                
                # B层
                report.append(f"\nB层（引燃层）- {formula['B层_引燃层']['重量']}")
                for comp, value in formula['B层_引燃层']['成分'].items():
                    report.append(f"  • {comp}: {value}")
                
                # C层
                report.append(f"\nC层（主体层）- {formula['C层_主体层']['重量']}")
                for comp, value in formula['C层_主体层']['成分'].items():
                    report.append(f"  • {comp}: {value}")
                
                # 工艺参数
                report.append("\n工艺参数:")
                for param, value in suggestion['process_params'].items():
                    report.append(f"  • {param}: {value}")
                
                # 预期性能
                report.append("\n预期性能:")
                for metric, value in suggestion['expected_performance'].items():
                    report.append(f"  • {metric}: {value}")
                
                # 优化说明
                if 'optimization_notes' in suggestion:
                    report.append("\n优化说明:")
                    for note in suggestion['optimization_notes']:
                        report.append(f"  ⚠️ {note}")
                
                report.append("\n" + "=" * 60)
        
        if 'AS9100D_reminder' in results:
            report.append(f"\n⚠️ {results['AS9100D_reminder']}")
        
        report_text = '\n'.join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        return report_text