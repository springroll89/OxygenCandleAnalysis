# modules/advanced_analysis/kinetics_analyzer.py
"""
反应动力学分析模块
分析氧烛反应的动力学特征，包括反应速率、活化能等
"""

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter
from scipy.integrate import cumtrapz
import matplotlib.pyplot as plt
from datetime import datetime

class KineticsAnalyzer:
    """反应动力学分析器"""
    
    def __init__(self):
        """初始化动力学分析器"""
        self.as9100d_limits = {
            'reaction_rate_min': 0.1,  # L/min²
            'reaction_rate_max': 2.0,   # L/min²
            'activation_energy': (50, 150),  # kJ/mol范围
            'reaction_order': (0.5, 2.0)  # 反应级数范围
        }

    def analyze(self, report_data, temperature_data=None, baseline_data=None):
        """
        综合动力学分析

        Parameters:
        report_data: dict或DataFrame，包含流量时间数据
        temperature_data: 可选，温度数据用于计算活化能
        baseline_data: 可选，基准曲线数据（DataFrame或dict）

        Returns:
        dict: 动力学分析结果
        """
        # 提取时间和流量数据
        if isinstance(report_data, dict):
            time = report_data.get('时间(s)', [])
            flow = report_data.get('平均流量L/Min', [])
        else:
            # 从DataFrame提取
            time = report_data['时间(s)'].values
            flow = report_data['平均流量L/Min'].values

        # 计算累计产氧量（升）
        dt = np.mean(np.diff(time)) if len(time) > 1 else 0.5  # 时间间隔
        cumulative_oxygen = np.cumsum(flow * dt / 60)  # 流量*时间/60 转换为升

        results = {
            '分析时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '数据点数': len(time),
            '时间数据': time,  # 保存时间数据
            '流量数据': flow,  # 保存流量数据
            '累计产氧量': cumulative_oxygen  # 新增累计产氧量
        }

        # 处理基准数据
        if baseline_data is not None:
            if isinstance(baseline_data, pd.DataFrame):
                results['基准时间'] = baseline_data['time'].values if 'time' in baseline_data.columns else None
                results['基准流量'] = baseline_data['flow'].values if 'flow' in baseline_data.columns else None
            elif isinstance(baseline_data, dict):
                results['基准时间'] = baseline_data.get('time')
                results['基准流量'] = baseline_data.get('flow')

        # 1. 反应速率分析
        rate_analysis = self.calculate_reaction_rate(time, flow)
        results.update(rate_analysis)

        # 2. 反应阶段划分
        phases = self.identify_reaction_phases(time, flow, rate_analysis['reaction_rate'])
        results['反应阶段'] = phases

        # 3. 反应级数判定
        order_analysis = self.determine_reaction_order(time, flow)
        results.update(order_analysis)

        # 4. 如果有温度数据，计算活化能
        if temperature_data is not None:
            activation = self.estimate_activation_energy(time, flow, temperature_data)
            results.update(activation)

        # 5. 动力学模型拟合
        model_fit = self.fit_kinetic_model(time, flow)
        results.update(model_fit)

        # 6. 计算关键点产氧量（新增）
        results['关键点分析'] = self.analyze_key_points(time, flow, cumulative_oxygen, rate_analysis['reaction_rate'])

        # 7. AS9100D合规性检查
        compliance = self.check_as9100d_compliance(results)
        results['AS9100D合规性'] = compliance

        return results

    def analyze_key_points(self, time, flow, cumulative_oxygen, reaction_rate):
        """
        分析关键点的产氧量

        Parameters:
        time: 时间数组
        flow: 流量数组
        cumulative_oxygen: 累计产氧量数组
        reaction_rate: 反应速率数组

        Returns:
        list: 关键点列表
        """
        key_points = []

        # 1. 反应启动点（速率首次超过阈值）
        threshold = 0.1  # L/min²
        for i in range(len(reaction_rate)):
            if reaction_rate[i] > threshold:
                key_points.append({
                    '事件': '反应启动',
                    '时间(s)': float(time[i]),
                    '累计产氧量(L)': float(cumulative_oxygen[i]),
                    '反应速率(L/min²)': float(reaction_rate[i]),
                    '流量(L/min)': float(flow[i])
                })
                break

        # 2. 速率峰值点
        max_rate_idx = np.argmax(reaction_rate)
        key_points.append({
            '事件': '速率峰值',
            '时间(s)': float(time[max_rate_idx]),
            '累计产氧量(L)': float(cumulative_oxygen[max_rate_idx]),
            '反应速率(L/min²)': float(reaction_rate[max_rate_idx]),
            '流量(L/min)': float(flow[max_rate_idx])
        })

        # 3. 流量峰值点
        max_flow_idx = np.argmax(flow)
        key_points.append({
            '事件': '流量峰值',
            '时间(s)': float(time[max_flow_idx]),
            '累计产氧量(L)': float(cumulative_oxygen[max_flow_idx]),
            '反应速率(L/min²)': float(reaction_rate[max_flow_idx]),
            '流量(L/min)': float(flow[max_flow_idx])
        })

        # 4. 速率降至峰值50%点
        peak_rate = reaction_rate[max_rate_idx]
        for i in range(max_rate_idx + 1, len(reaction_rate)):
            if reaction_rate[i] < peak_rate * 0.5:
                key_points.append({
                    '事件': '速率降至50%',
                    '时间(s)': float(time[i]),
                    '累计产氧量(L)': float(cumulative_oxygen[i]),
                    '反应速率(L/min²)': float(reaction_rate[i]),
                    '流量(L/min)': float(flow[i])
                })
                break

        # 5. 产氧量达到50%点
        total_oxygen = cumulative_oxygen[-1]
        for i in range(len(cumulative_oxygen)):
            if cumulative_oxygen[i] >= total_oxygen * 0.5:
                key_points.append({
                    '事件': '产氧量达50%',
                    '时间(s)': float(time[i]),
                    '累计产氧量(L)': float(cumulative_oxygen[i]),
                    '反应速率(L/min²)': float(reaction_rate[i]),
                    '流量(L/min)': float(flow[i])
                })
                break

        # 6. 反应结束点
        key_points.append({
            '事件': '反应结束',
            '时间(s)': float(time[-1]),
            '累计产氧量(L)': float(cumulative_oxygen[-1]),
            '反应速率(L/min²)': float(reaction_rate[-1]),
            '流量(L/min)': float(flow[-1])
        })

        return key_points

    def calculate_reaction_rate(self, time, flow):
        """计算反应速率和加速度"""
        # 增强的平滑处理
        if len(flow) > 51:
            # 使用更大的窗口进行平滑
            flow_smooth = savgol_filter(flow, window_length=51, polyorder=3)
        elif len(flow) > 21:
            flow_smooth = savgol_filter(flow, window_length=21, polyorder=3)
        elif len(flow) > 11:
            flow_smooth = savgol_filter(flow, window_length=11, polyorder=3)
        else:
            flow_smooth = flow

        # 计算一阶导数（反应速率）
        dt = np.mean(np.diff(time))
        reaction_rate_raw = np.gradient(flow_smooth, dt)

        # 对反应速率进行二次平滑（关键改进）
        if len(reaction_rate_raw) > 51:
            # 分段平滑：初期使用较小窗口，后期使用较大窗口
            reaction_rate = np.zeros_like(reaction_rate_raw)

            # 初期（前200个点，约100秒）- 保留较多细节
            if len(reaction_rate_raw) > 200:
                reaction_rate[:200] = savgol_filter(
                    reaction_rate_raw[:200],
                    window_length=min(21, len(reaction_rate_raw[:200]) // 2 * 2 - 1),
                    polyorder=3
                )
                # 中后期 - 强平滑
                reaction_rate[200:] = savgol_filter(
                    reaction_rate_raw[200:],
                    window_length=min(51, len(reaction_rate_raw[200:]) // 2 * 2 - 1),
                    polyorder=3
                )
            else:
                reaction_rate = savgol_filter(
                    reaction_rate_raw,
                    window_length=min(21, len(reaction_rate_raw) // 2 * 2 - 1),
                    polyorder=3
                )
        else:
            reaction_rate = reaction_rate_raw

        # 计算二阶导数（反应加速度）- 也需要平滑
        if len(reaction_rate) > 11:
            reaction_accel = savgol_filter(
                np.gradient(reaction_rate, dt),
                window_length=11,
                polyorder=3
            )
        else:
            reaction_accel = np.gradient(reaction_rate, dt)

        # 找出关键点
        max_rate_idx = np.argmax(reaction_rate)
        min_rate_idx = np.argmin(reaction_rate)

        # 计算反应活性指标
        startup_activity = np.mean(reaction_rate[:20]) if len(reaction_rate) > 20 else 0
        steady_activity = np.std(reaction_rate[100:900]) if len(reaction_rate) > 900 else 0

        return {
            'reaction_rate': reaction_rate,
            'reaction_rate_raw': reaction_rate_raw,  # 保留原始数据供参考
            'reaction_acceleration': reaction_accel,
            'max_reaction_rate': float(reaction_rate[max_rate_idx]),
            'max_rate_time': float(time[max_rate_idx]),
            'min_reaction_rate': float(reaction_rate[min_rate_idx]),
            'min_rate_time': float(time[min_rate_idx]),
            'startup_activity': float(startup_activity),
            'steady_state_variability': float(steady_activity),
            'rate_stability_cv': float(np.std(reaction_rate[100:900]) / np.mean(np.abs(reaction_rate[100:900])))
            if len(reaction_rate) > 900 else None
        }
    
    def identify_reaction_phases(self, time, flow, reaction_rate):
        """识别反应阶段"""
        phases = []
        
        # 定义阶段判定标准
        flow_threshold = 0.5  # L/min
        rate_threshold = 0.01  # L/min²
        
        # 1. 诱导期（点火到流量开始上升）
        induction_end = None
        for i, f in enumerate(flow):
            if f > flow_threshold:
                induction_end = i
                break
        
        if induction_end:
            phases.append({
                'name': '诱导期',
                'start_time': 0,
                'end_time': float(time[induction_end]),
                'duration': float(time[induction_end]),
                'characteristics': '点火引燃阶段'
            })
        
        # 2. 加速期（流量快速上升）
        if induction_end:
            accel_start = induction_end
            # 找到反应速率开始下降的点
            for i in range(accel_start + 10, len(reaction_rate)):
                if reaction_rate[i] < reaction_rate[i-5] * 0.8:  # 速率下降20%
                    accel_end = i
                    phases.append({
                        'name': '加速期',
                        'start_time': float(time[accel_start]),
                        'end_time': float(time[accel_end]),
                        'duration': float(time[accel_end] - time[accel_start]),
                        'characteristics': '反应快速发展'
                    })
                    break
        
        # 3. 稳定期（流量相对稳定）
        stable_start = None
        stable_end = None
        
        # 找稳定段（CV值小于10%的连续段）
        window = 60  # 30秒窗口（0.5秒采样）
        for i in range(100, len(flow) - window):
            window_data = flow[i:i+window]
            cv = np.std(window_data) / np.mean(window_data)
            if cv < 0.1 and stable_start is None:
                stable_start = i
            elif cv > 0.15 and stable_start is not None and stable_end is None:
                stable_end = i
                break
        
        if stable_start:
            if stable_end is None:
                stable_end = len(flow) - 100
            phases.append({
                'name': '稳定期',
                'start_time': float(time[stable_start]),
                'end_time': float(time[stable_end]),
                'duration': float(time[stable_end] - time[stable_start]),
                'characteristics': '稳定产氧'
            })
        
        # 4. 衰减期（反应末期）
        if stable_end and stable_end < len(flow) - 50:
            phases.append({
                'name': '衰减期',
                'start_time': float(time[stable_end]),
                'end_time': float(time[-1]),
                'duration': float(time[-1] - time[stable_end]),
                'characteristics': '反应逐渐停止'
            })
        
        return phases
    
    def determine_reaction_order(self, time, flow):
        """判定反应级数"""
        # 使用积分法判定反应级数
        # 对于不同级数，积分形式不同
        
        # 累积产氧量（反应物消耗量的代理）
        cumulative = cumtrapz(flow, time, initial=0) / 60  # 转换为升
        max_oxygen = cumulative[-1]
        
        # 反应物剩余量（假设与剩余产氧能力成正比）
        remaining = max_oxygen - cumulative
        remaining[remaining <= 0] = 1e-6  # 避免对数计算问题
        
        # 准备数据（取稳定段）
        stable_start = 100
        stable_end = min(1000, len(time) - 100)
        
        t_fit = time[stable_start:stable_end]
        remaining_fit = remaining[stable_start:stable_end]
        
        # 尝试不同反应级数的线性化
        models = {}
        
        # 零级反应: [A] = [A]0 - kt
        try:
            popt_0, pcov_0 = curve_fit(lambda t, k, a0: a0 - k*t, 
                                       t_fit, remaining_fit)
            models['零级'] = {
                'k': popt_0[0],
                'R²': self._calculate_r2(remaining_fit, popt_0[1] - popt_0[0]*t_fit)
            }
        except:
            models['零级'] = {'k': 0, 'R²': 0}
        
        # 一级反应: ln[A] = ln[A]0 - kt
        try:
            ln_remaining = np.log(remaining_fit)
            popt_1, pcov_1 = curve_fit(lambda t, k, lna0: lna0 - k*t,
                                       t_fit, ln_remaining)
            models['一级'] = {
                'k': popt_1[0],
                'R²': self._calculate_r2(ln_remaining, popt_1[1] - popt_1[0]*t_fit)
            }
        except:
            models['一级'] = {'k': 0, 'R²': 0}
        
        # 二级反应: 1/[A] = 1/[A]0 + kt
        try:
            inv_remaining = 1 / remaining_fit
            popt_2, pcov_2 = curve_fit(lambda t, k, inv_a0: inv_a0 + k*t,
                                       t_fit, inv_remaining)
            models['二级'] = {
                'k': popt_2[0],
                'R²': self._calculate_r2(inv_remaining, popt_2[1] + popt_2[0]*t_fit)
            }
        except:
            models['二级'] = {'k': 0, 'R²': 0}
        
        # 选择最佳模型
        best_order = max(models.items(), key=lambda x: x[1]['R²'])
        
        # 计算表观反应级数（使用幂律模型）
        try:
            # r = k * C^n，取对数：log(r) = log(k) + n*log(C)
            valid_idx = (flow[stable_start:stable_end] > 0.1)
            if np.sum(valid_idx) > 10:
                log_rate = np.log(flow[stable_start:stable_end][valid_idx])
                log_conc = np.log(remaining_fit[valid_idx])
                popt_n, _ = curve_fit(lambda x, n, logk: logk + n*x,
                                      log_conc, log_rate)
                apparent_order = popt_n[0]
            else:
                apparent_order = None
        except:
            apparent_order = None
        
        return {
            'reaction_order_model': best_order[0],
            'rate_constant': best_order[1]['k'],
            'model_R2': best_order[1]['R²'],
            'apparent_reaction_order': apparent_order,
            'all_models': models
        }
    
    def estimate_activation_energy(self, time, flow, temperature_data):
        """估算活化能（使用Arrhenius方程）"""
        # Arrhenius方程: k = A * exp(-Ea/RT)
        # ln(k) = ln(A) - Ea/RT
        
        R = 8.314  # J/(mol·K)
        
        # 获取不同温度下的反应速率常数
        if isinstance(temperature_data, pd.DataFrame):
            # 假设有多个温度的数据
            temps = temperature_data.columns
            rate_constants = []
            
            for temp_col in temps:
                if 'CH' in temp_col:  # 温度通道
                    avg_temp = temperature_data[temp_col].mean() + 273.15  # 转换为K
                    # 这里简化处理，实际需要对应时间段的速率常数
                    k = np.mean(flow[100:500]) / 100  # 简化的速率常数
                    rate_constants.append((1/avg_temp, np.log(k)))
        else:
            # 单一温度数据
            avg_temp = np.mean(temperature_data) + 273.15
            k = np.mean(flow[100:500]) / 100
            
            # 需要至少两个温度点才能计算活化能
            # 这里使用温度变化来估算
            temp_range = np.max(temperature_data) - np.min(temperature_data)
            if temp_range > 10:  # 温度变化超过10度
                # 使用前后两段的数据
                t1 = np.mean(temperature_data[:len(temperature_data)//2]) + 273.15
                t2 = np.mean(temperature_data[len(temperature_data)//2:]) + 273.15
                k1 = np.mean(flow[:len(flow)//2]) / 100
                k2 = np.mean(flow[len(flow)//2:]) / 100
                
                if k1 > 0 and k2 > 0:
                    # 使用两点法计算活化能
                    Ea = -R * (np.log(k2) - np.log(k1)) / (1/t2 - 1/t1) / 1000  # kJ/mol
                else:
                    Ea = None
            else:
                Ea = None
        
        # 计算频率因子
        if Ea:
            A = k * np.exp(Ea * 1000 / (R * avg_temp))
        else:
            A = None
        
        return {
            'activation_energy_kJ_mol': Ea,
            'frequency_factor': A,
            'arrhenius_R2': None  # 如果有多个温度点，可以计算R²
        }
    
    def fit_kinetic_model(self, time, flow):
        """拟合动力学模型"""
        # 尝试多种动力学模型
        models = {}
        
        # 1. Avrami-Erofeev模型（固相反应）
        # α = 1 - exp(-(kt)^n)
        try:
            cumulative = cumtrapz(flow, time, initial=0) / 60
            alpha = cumulative / cumulative[-1] if cumulative[-1] > 0 else cumulative
            
            # 线性化：ln(-ln(1-α)) = n*ln(k) + n*ln(t)
            valid_idx = (alpha > 0.05) & (alpha < 0.95)
            if np.sum(valid_idx) > 10:
                y = np.log(-np.log(1 - alpha[valid_idx]))
                x = np.log(time[valid_idx])
                popt, _ = curve_fit(lambda x, n, lnk: n*lnk + n*x, x, y)
                
                models['Avrami-Erofeev'] = {
                    'n': popt[0],
                    'k': np.exp(popt[1]),
                    'type': '成核生长模型'
                }
        except:
            pass
        
        # 2. 收缩核模型（适用于多相反应）
        # 1 - (1-α)^(1/3) = kt
        try:
            valid_idx = alpha < 0.99
            y = 1 - (1 - alpha[valid_idx])**(1/3)
            popt, _ = curve_fit(lambda t, k: k*t, time[valid_idx], y)
            
            models['收缩核模型'] = {
                'k': popt[0],
                'type': '界面反应控制'
            }
        except:
            pass
        
        # 3. 扩散控制模型
        # α² = kt (二维扩散)
        try:
            y = alpha**2
            popt, _ = curve_fit(lambda t, k: k*t, time, y)
            
            models['扩散模型'] = {
                'k': popt[0],
                'type': '扩散控制'
            }
        except:
            pass
        
        return {
            'kinetic_models': models,
            'best_model': max(models.keys()) if models else None
        }
    
    def _calculate_r2(self, y_true, y_pred):
        """计算R²值"""
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        return 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    def check_as9100d_compliance(self, results):
        """检查AS9100D标准合规性"""
        compliance = {
            'status': 'PASS',
            'issues': [],
            'warnings': []
        }
        
        # 检查反应速率
        max_rate = results.get('max_reaction_rate', 0)
        if max_rate < self.as9100d_limits['reaction_rate_min']:
            compliance['issues'].append(f'反应速率过低: {max_rate:.3f} < {self.as9100d_limits["reaction_rate_min"]}')
            compliance['status'] = 'FAIL'
        elif max_rate > self.as9100d_limits['reaction_rate_max']:
            compliance['warnings'].append(f'反应速率偏高: {max_rate:.3f} > {self.as9100d_limits["reaction_rate_max"]}')
        
        # 检查反应级数
        apparent_order = results.get('apparent_reaction_order')
        if apparent_order:
            if apparent_order < self.as9100d_limits['reaction_order'][0]:
                compliance['warnings'].append(f'反应级数偏低: {apparent_order:.2f}')
            elif apparent_order > self.as9100d_limits['reaction_order'][1]:
                compliance['warnings'].append(f'反应级数偏高: {apparent_order:.2f}')
        
        # 检查稳定性
        rate_cv = results.get('rate_stability_cv')
        if rate_cv and rate_cv > 0.2:
            compliance['issues'].append(f'反应速率变异系数过大: CV={rate_cv:.3f}')
            compliance['status'] = 'FAIL'
        
        return compliance
    
    def generate_kinetics_report(self, results, output_path=None):
        """生成动力学分析报告"""
        report = []
        report.append("=" * 60)
        report.append("反应动力学分析报告")
        report.append("=" * 60)
        report.append(f"分析时间: {results['分析时间']}")
        report.append(f"数据点数: {results['数据点数']}")
        
        report.append("\n【反应速率分析】")
        report.append(f"最大反应速率: {results['max_reaction_rate']:.3f} L/min² @ {results['max_rate_time']:.1f}s")
        report.append(f"最小反应速率: {results['min_reaction_rate']:.3f} L/min² @ {results['min_rate_time']:.1f}s")
        report.append(f"启动活性: {results['startup_activity']:.3f}")
        report.append(f"稳态变异性: {results['steady_state_variability']:.3f}")
        
        report.append("\n【反应阶段】")
        for phase in results['反应阶段']:
            report.append(f"- {phase['name']}: {phase['start_time']:.1f}s - {phase['end_time']:.1f}s ({phase['duration']:.1f}s)")
            report.append(f"  特征: {phase['characteristics']}")
        
        report.append("\n【反应级数】")
        report.append(f"最佳模型: {results['reaction_order_model']}")
        report.append(f"速率常数: {results['rate_constant']:.6f}")
        report.append(f"模型R²: {results['model_R2']:.4f}")
        if results.get('apparent_reaction_order'):
            report.append(f"表观反应级数: {results['apparent_reaction_order']:.2f}")
        
        if results.get('activation_energy_kJ_mol'):
            report.append("\n【活化能分析】")
            report.append(f"活化能: {results['activation_energy_kJ_mol']:.1f} kJ/mol")
            if results.get('frequency_factor'):
                report.append(f"频率因子: {results['frequency_factor']:.2e}")
        
        report.append("\n【AS9100D合规性】")
        compliance = results['AS9100D合规性']
        report.append(f"状态: {compliance['status']}")
        if compliance['issues']:
            report.append("问题:")
            for issue in compliance['issues']:
                report.append(f"  - {issue}")
        if compliance['warnings']:
            report.append("警告:")
            for warning in compliance['warnings']:
                report.append(f"  - {warning}")
        
        report_text = '\n'.join(report)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"报告已保存: {output_path}")
        
        return report_text