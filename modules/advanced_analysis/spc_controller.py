# modules/advanced_analysis/spc_controller.py
"""
SPC统计过程控制模块
用于分析批次间一致性和过程能力
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

class SPCController:
    """统计过程控制器"""
    
    def __init__(self, spec_limits=None):
        """
        初始化SPC控制器
        
        Parameters:
        spec_limits: 规格限制字典
        """
        self.spec_limits = spec_limits or {
            '产氧时间': {'LSL': 22, 'USL': 35, 'target': 25},  # 分钟
            '达标率': {'LSL': 95, 'USL': 100, 'target': 100},  # %
            '外壳温度': {'LSL': None, 'USL': 230, 'target': 180},  # °C
            '启动时长': {'LSL': None, 'USL': 2, 'target': 1},  # 秒
            '达峰时长': {'LSL': None, 'USL': 10, 'target': 5}  # 秒
        }
        
        # AS9100D要求的最小过程能力指数
        self.min_cpk = 1.33
        self.min_cp = 1.33
        
    def analyze_batch_consistency(self, batch_data):
        """
        分析批次一致性
        
        Parameters:
        batch_data: DataFrame，包含多批次数据
        
        Returns:
        dict: 一致性分析结果
        """
        results = {
            '批次数': len(batch_data),
            '分析时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '控制图': {},
            '过程能力': {},
            '一致性指标': {},
            'AS9100D合规性': {}
        }
        
        # 关键指标列表
        key_metrics = ['产氧时间(分钟)', '达标率(%)', '外壳最高温度(°C)', 
                      '启动时长(秒)', '达峰时长(秒)']
        
        for metric in key_metrics:
            if metric in batch_data.columns:
                # 清理指标名称用于匹配规格限
                clean_name = metric.replace('(分钟)', '').replace('(%)', '').replace('(°C)', '').replace('(秒)', '')
                
                # 获取数据
                data = batch_data[metric].dropna().values
                
                if len(data) < 3:
                    continue
                
                # 1. 创建控制图
                control_chart = self.create_control_chart(data, clean_name)
                results['控制图'][clean_name] = control_chart
                
                # 2. 计算过程能力
                if clean_name in self.spec_limits:
                    capability = self.calculate_process_capability(
                        data, 
                        self.spec_limits[clean_name]
                    )
                    results['过程能力'][clean_name] = capability
                
                # 3. 批次间一致性分析
                consistency = self.analyze_consistency(data)
                results['一致性指标'][clean_name] = consistency
        
        # 4. 综合评估
        results['综合评估'] = self.overall_assessment(results)
        
        # 5. AS9100D合规性检查
        results['AS9100D合规性'] = self.check_as9100d_compliance(results)
        
        return results
    
    def create_control_chart(self, data, metric_name):
        """创建控制图（X-bar和R图）"""
        n = len(data)
        
        # 计算均值和标准差
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        # 计算控制限（3σ原则）
        ucl = mean + 3 * std
        lcl = mean - 3 * std
        
        # 计算警告限（2σ）
        uwl = mean + 2 * std
        lwl = mean - 2 * std
        
        # 计算移动极差
        mr = np.abs(np.diff(data))
        mr_mean = np.mean(mr)
        mr_ucl = mr_mean * 3.267  # D4 for n=2
        
        # 检测失控点
        out_of_control = []
        
        # Rule 1: 点超出控制限
        for i, point in enumerate(data):
            if point > ucl or point < lcl:
                out_of_control.append({
                    'index': i,
                    'value': point,
                    'rule': '超出控制限'
                })
        
        # Rule 2: 连续7点在中心线同一侧
        above_mean = data > mean
        for i in range(len(data) - 6):
            if all(above_mean[i:i+7]) or all(~above_mean[i:i+7]):
                out_of_control.append({
                    'index': i,
                    'rule': '7点同侧'
                })
        
        # Rule 3: 连续6点递增或递减
        for i in range(len(data) - 5):
            segment = data[i:i+6]
            if all(np.diff(segment) > 0) or all(np.diff(segment) < 0):
                out_of_control.append({
                    'index': i,
                    'rule': '6点趋势'
                })
        
        # CUSUM控制图
        cusum = self.calculate_cusum(data, mean)
        
        # EWMA控制图
        ewma = self.calculate_ewma(data)
        
        return {
            'mean': mean,
            'std': std,
            'UCL': ucl,
            'LCL': lcl,
            'UWL': uwl,
            'LWL': lwl,
            'MR_mean': mr_mean,
            'MR_UCL': mr_ucl,
            'out_of_control': out_of_control,
            'CUSUM': cusum,
            'EWMA': ewma,
            'in_control': len(out_of_control) == 0
        }
    
    def calculate_cusum(self, data, target):
        """计算累积和控制图"""
        k = 0.5 * np.std(data)  # 参考值
        h = 5 * np.std(data)    # 决策区间
        
        cusum_pos = np.zeros(len(data))
        cusum_neg = np.zeros(len(data))
        
        for i in range(1, len(data)):
            cusum_pos[i] = max(0, data[i] - (target + k) + cusum_pos[i-1])
            cusum_neg[i] = max(0, (target - k) - data[i] + cusum_neg[i-1])
        
        # 检测失控
        ooc_points = []
        for i in range(len(data)):
            if cusum_pos[i] > h or cusum_neg[i] > h:
                ooc_points.append(i)
        
        return {
            'C+': cusum_pos,
            'C-': cusum_neg,
            'h': h,
            'out_of_control': ooc_points
        }
    
    def calculate_ewma(self, data, lambda_param=0.2):
        """计算指数加权移动平均控制图"""
        ewma = np.zeros(len(data))
        ewma[0] = data[0]
        
        for i in range(1, len(data)):
            ewma[i] = lambda_param * data[i] + (1 - lambda_param) * ewma[i-1]
        
        # 计算控制限
        mean = np.mean(data)
        std = np.std(data)
        
        # EWMA控制限随时间变化
        ucl = np.zeros(len(data))
        lcl = np.zeros(len(data))
        
        for i in range(len(data)):
            var_ewma = (lambda_param / (2 - lambda_param)) * (1 - (1 - lambda_param)**(2*(i+1)))
            ucl[i] = mean + 3 * std * np.sqrt(var_ewma)
            lcl[i] = mean - 3 * std * np.sqrt(var_ewma)
        
        return {
            'EWMA': ewma,
            'UCL': ucl,
            'LCL': lcl,
            'lambda': lambda_param
        }
    
    def calculate_process_capability(self, data, spec_limits):
        """计算过程能力指数"""
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        # 获取规格限
        lsl = spec_limits.get('LSL')
        usl = spec_limits.get('USL')
        target = spec_limits.get('target', mean)
        
        capability = {}
        
        # Cp - 过程能力指数
        if lsl is not None and usl is not None:
            cp = (usl - lsl) / (6 * std)
            capability['Cp'] = round(cp, 3)
        else:
            cp = None
        
        # Cpk - 过程能力指数（考虑偏移）
        cpu = None
        cpl = None
        
        if usl is not None:
            cpu = (usl - mean) / (3 * std)
            
        if lsl is not None:
            cpl = (mean - lsl) / (3 * std)
        
        if cpu is not None and cpl is not None:
            cpk = min(cpu, cpl)
        elif cpu is not None:
            cpk = cpu
        elif cpl is not None:
            cpk = cpl
        else:
            cpk = None
        
        if cpk is not None:
            capability['Cpk'] = round(cpk, 3)
            capability['Cpu'] = round(cpu, 3) if cpu else None
            capability['Cpl'] = round(cpl, 3) if cpl else None
        
        # Cpm - 目标过程能力指数
        if target is not None:
            variance_from_target = std**2 + (mean - target)**2
            if lsl is not None and usl is not None:
                cpm = (usl - lsl) / (6 * np.sqrt(variance_from_target))
                capability['Cpm'] = round(cpm, 3)
        
        # Pp和Ppk - 过程性能指数
        if lsl is not None and usl is not None:
            pp = (usl - lsl) / (6 * std)
            capability['Pp'] = round(pp, 3)
            
            ppu = (usl - mean) / (3 * std) if usl is not None else None
            ppl = (mean - lsl) / (3 * std) if lsl is not None else None
            
            if ppu is not None and ppl is not None:
                ppk = min(ppu, ppl)
            elif ppu is not None:
                ppk = ppu
            elif ppl is not None:
                ppk = ppl
            else:
                ppk = None
                
            if ppk is not None:
                capability['Ppk'] = round(ppk, 3)
        
        # 不合格品率估算（ppm）
        if lsl is not None:
            p_below_lsl = stats.norm.cdf(lsl, mean, std)
        else:
            p_below_lsl = 0
            
        if usl is not None:
            p_above_usl = 1 - stats.norm.cdf(usl, mean, std)
        else:
            p_above_usl = 0
        
        ppm = (p_below_lsl + p_above_usl) * 1e6
        capability['PPM'] = round(ppm, 1)
        
        # 西格玛水平
        if ppm > 0:
            # 简化计算，实际应考虑1.5σ偏移
            sigma_level = -stats.norm.ppf(ppm / 1e6) + 1.5
            capability['Sigma_Level'] = round(sigma_level, 2)
        
        return capability
    
    def analyze_consistency(self, data):
        """分析数据一致性"""
        consistency = {}
        
        # 变异系数
        cv = np.std(data) / np.mean(data) if np.mean(data) != 0 else np.inf
        consistency['CV'] = round(cv * 100, 2)  # 百分比
        
        # 极差
        consistency['Range'] = round(np.max(data) - np.min(data), 3)
        
        # 四分位距
        q1, q3 = np.percentile(data, [25, 75])
        iqr = q3 - q1
        consistency['IQR'] = round(iqr, 3)
        
        # 偏度和峰度
        consistency['Skewness'] = round(stats.skew(data), 3)
        consistency['Kurtosis'] = round(stats.kurtosis(data), 3)
        
        # 正态性检验
        if len(data) >= 3:
            statistic, p_value = stats.shapiro(data)
            consistency['Normality_Test'] = {
                'statistic': round(statistic, 4),
                'p_value': round(p_value, 4),
                'is_normal': p_value > 0.05
            }
        
        # 稳定性评级
        if cv < 0.05:
            stability = '优秀'
        elif cv < 0.10:
            stability = '良好'
        elif cv < 0.15:
            stability = '合格'
        else:
            stability = '需改进'
        
        consistency['Stability_Rating'] = stability
        
        return consistency
    
    def check_as9100d_compliance(self, results):
        """检查AS9100D合规性"""
        compliance = {
            'overall_status': 'PASS',
            'details': {},
            'required_actions': []
        }
        
        # 检查过程能力
        for metric, capability in results['过程能力'].items():
            metric_compliance = {
                'status': 'PASS',
                'issues': []
            }
            
            # 检查Cpk
            cpk = capability.get('Cpk')
            if cpk is not None:
                if cpk < 1.0:
                    metric_compliance['status'] = 'FAIL'
                    metric_compliance['issues'].append(f'Cpk = {cpk} < 1.0 (不可接受)')
                    compliance['required_actions'].append(f'{metric}: 立即采取纠正措施')
                elif cpk < self.min_cpk:
                    metric_compliance['status'] = 'WARNING'
                    metric_compliance['issues'].append(f'Cpk = {cpk} < {self.min_cpk} (需改进)')
                    compliance['required_actions'].append(f'{metric}: 制定改进计划')
            
            # 检查PPM
            ppm = capability.get('PPM')
            if ppm is not None and ppm > 63:  # 6σ对应约63ppm
                metric_compliance['issues'].append(f'PPM = {ppm} > 63 (未达6σ水平)')
            
            compliance['details'][metric] = metric_compliance
            
            if metric_compliance['status'] == 'FAIL':
                compliance['overall_status'] = 'FAIL'
            elif metric_compliance['status'] == 'WARNING' and compliance['overall_status'] != 'FAIL':
                compliance['overall_status'] = 'WARNING'
        
        # 检查控制状态
        for metric, chart in results['控制图'].items():
            if not chart['in_control']:
                compliance['details'][metric]['issues'].append('过程失控')
                compliance['required_actions'].append(f'{metric}: 调查失控原因')
        
        return compliance
    
    def overall_assessment(self, results):
        """综合评估"""
        assessment = {
            'process_stability': [],
            'process_capability': [],
            'recommendations': []
        }
        
        # 稳定性评估
        in_control_count = sum(1 for chart in results['控制图'].values() if chart['in_control'])
        total_charts = len(results['控制图'])
        
        if total_charts > 0:
            control_rate = in_control_count / total_charts
            if control_rate == 1.0:
                assessment['process_stability'] = '所有过程处于统计控制状态'
            elif control_rate >= 0.8:
                assessment['process_stability'] = '大部分过程稳定，个别需关注'
            else:
                assessment['process_stability'] = '多个过程失控，需要立即改进'
        
        # 能力评估
        high_capability = []
        low_capability = []
        
        for metric, capability in results['过程能力'].items():
            cpk = capability.get('Cpk')
            if cpk:
                if cpk >= 1.67:
                    high_capability.append(metric)
                elif cpk < 1.33:
                    low_capability.append(metric)
        
        if high_capability:
            assessment['process_capability'].append(f'高能力过程: {", ".join(high_capability)}')
        if low_capability:
            assessment['process_capability'].append(f'需改进过程: {", ".join(low_capability)}')
        
        # 生成建议
        for metric in low_capability:
            consistency = results['一致性指标'].get(metric, {})
            cv = consistency.get('CV', 0)
            
            if cv > 15:
                assessment['recommendations'].append(
                    f'{metric}: 变异过大(CV={cv}%)，建议检查原料一致性和工艺参数'
                )
            
            chart = results['控制图'].get(metric, {})
            if chart.get('out_of_control'):
                assessment['recommendations'].append(
                    f'{metric}: 发现{len(chart["out_of_control"])}个失控点，需要根因分析'
                )
        
        return assessment
    
    def generate_spc_report(self, results, output_path=None):
        """生成SPC报告"""
        # 创建HTML报告
        html_content = self._create_html_report(results)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"SPC报告已保存: {output_path}")
        
        return html_content
    
    def _create_html_report(self, results):
        """创建HTML格式的报告"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SPC分析报告</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .pass {{ color: green; font-weight: bold; }}
                .fail {{ color: red; font-weight: bold; }}
                .warning {{ color: orange; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>批次一致性SPC分析报告</h1>
            <p>分析时间: {results['分析时间']}</p>
            <p>批次数量: {results['批次数']}</p>
            
            <h2>AS9100D合规性</h2>
            <p>总体状态: <span class="{results['AS9100D合规性']['overall_status'].lower()}">{results['AS9100D合规性']['overall_status']}</span></p>
        """
        
        # 添加过程能力表
        if results['过程能力']:
            html += "<h2>过程能力分析</h2><table><tr><th>指标</th><th>Cp</th><th>Cpk</th><th>PPM</th><th>Sigma Level</th></tr>"
            
            for metric, capability in results['过程能力'].items():
                html += f"""
                <tr>
                    <td>{metric}</td>
                    <td>{capability.get('Cp', '-')}</td>
                    <td>{capability.get('Cpk', '-')}</td>
                    <td>{capability.get('PPM', '-')}</td>
                    <td>{capability.get('Sigma_Level', '-')}</td>
                </tr>
                """
            html += "</table>"
        
        # 添加综合评估
        assessment = results.get('综合评估', {})
        if assessment:
            html += "<h2>综合评估</h2>"
            html += f"<p><b>过程稳定性:</b> {assessment.get('process_stability', '')}</p>"
            
            if assessment.get('recommendations'):
                html += "<h3>改进建议</h3><ul>"
                for rec in assessment['recommendations']:
                    html += f"<li>{rec}</li>"
                html += "</ul>"
        
        html += "</body></html>"
        
        return html