#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评价系统模块 - 氧烛产品性能综合评价
路径: .
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os

class OxygenCandleEvaluator:
    """氧烛产品性能评价系统"""
    
    def __init__(self, config_file=None):
        """
        初始化评价系统
        
        Parameters:
        config_file: 配置文件路径（可选）
        """
        # 默认配置
        self.config = {
            'baseline_max_time': 1320,  # 基准曲线最大时长（秒）
            'weights': {
                'baseline_conformity': 0.5,   # 基准符合度权重
                'duration_compliance': 0.3,   # 时长达标度权重
                'temperature_safety': 0.2     # 温度安全度权重
            },
            'thresholds': {
                'shell_temp': {
                    '优秀': 60,
                    '良好': 80,
                    '合格': 100,
                    '极限': 120
                },
                'insulation_temp': {
                    '优秀': 80,
                    '良好': 100,
                    '合格': 120,
                    '极限': 150
                },
                'outlet_temp': {
                    '优秀': 100,
                    '良好': 120,
                    '合格': 150,
                    '极限': 180
                },
                'compliance_rate': {
                    '优秀': 95,
                    '良好': 85,
                    '合格': 75,
                    '不合格': 0
                },
                'cv_value': {
                    '优秀': 0.05,
                    '良好': 0.10,
                    '合格': 0.15,
                    '不合格': 1.0
                }
            }
        }
        
        # 如果提供了配置文件，加载配置
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)
    
    def load_config(self, config_file):
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                custom_config = json.load(f)
                # 更新配置
                if 'analysis' in custom_config:
                    self.config.update(custom_config['analysis'])
            print(f"✅ 已加载配置文件: {config_file}")
        except Exception as e:
            print(f"⚠️ 加载配置文件失败: {e}")
    
    def evaluate_product(self, data):
        """
        评价单个产品
        
        Parameters:
        data: dict, 包含产品测试数据
        
        Returns:
        dict: 评价结果
        """
        result = {
            '产品编号': data.get('实验编号', ''),
            '配方代号': data.get('配方代号', ''),
            '工艺代号': data.get('工艺代号', ''),
            '评价时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 1. 计算基准符合度
        baseline_score = self.calculate_baseline_conformity(data)
        result.update(baseline_score)
        
        # 2. 计算时长达标度
        duration_score = self.calculate_duration_compliance(data)
        result.update(duration_score)
        
        # 3. 计算温度安全度
        temp_score = self.calculate_temperature_safety(data)
        result.update(temp_score)
        
        # 4. 计算综合得分
        total_score = (
            self.config['weights']['baseline_conformity'] * result['基准符合度'] +
            self.config['weights']['duration_compliance'] * result['时长达标度'] +
            self.config['weights']['temperature_safety'] * result['温度安全度']
        )
        
        result['综合得分'] = round(total_score, 3)
        result['评级'] = self.get_rating(total_score)
        
        # 5. 添加详细指标
        result['权重配置'] = self.config['weights'].copy()
        result['不足之处'] = self.identify_weaknesses(result)
        result['优势特点'] = self.identify_strengths(result)
        result['改进建议'] = self.generate_recommendations(result)
        
        return result
    
    def calculate_baseline_conformity(self, data):
        """计算基准符合度"""
        result = {}
        
        # 主要指标：平均达标率
        compliance_rate = data.get('平均达标率(%)', 0) / 100
        
        # 辅助指标1：关键时间点的流量比
        flow_360 = data.get('360秒平均总流量(L)', 0)
        baseline_360 = data.get('360秒基准总流量(L)', 1)
        ratio_360 = flow_360 / baseline_360 if baseline_360 > 0 else 0
        
        flow_1200 = data.get('1200秒平均总流量(L)', 0)
        baseline_1200 = data.get('1200秒基准总流量(L)', 1)
        ratio_1200 = flow_1200 / baseline_1200 if baseline_1200 > 0 else 0
        
        # 辅助指标2：总产氧量比
        total_oxygen = data.get('总累积供氧(升)', 0)
        expected_oxygen = 110  # 基准期望值（可调整）
        oxygen_ratio = min(total_oxygen / expected_oxygen, 1.2) if expected_oxygen > 0 else 0
        
        # 辅助指标3：CV值（稳定性）
        cv_value = data.get('CV值', 0.1)
        cv_score = self.calculate_cv_score(cv_value)
        
        # 综合计算基准符合度
        baseline_conformity = (
            0.5 * compliance_rate +      # 达标率占50%
            0.15 * ratio_360 +           # 360秒流量比占15%
            0.15 * ratio_1200 +          # 1200秒流量比占15%
            0.1 * oxygen_ratio +         # 总产氧量比占10%
            0.1 * cv_score               # 稳定性占10%
        )
        
        result['基准符合度'] = round(baseline_conformity, 3)
        result['平均达标率(%)'] = round(compliance_rate * 100, 1)
        result['360秒流量比'] = round(ratio_360, 3)
        result['1200秒流量比'] = round(ratio_1200, 3)
        result['总产氧量(L)'] = round(total_oxygen, 1)
        result['CV值'] = round(cv_value, 4)
        
        # 基准符合度细分评价
        result['基准符合评价'] = self.get_level_evaluation(
            baseline_conformity, 
            [0.95, 0.85, 0.75]
        )
        
        return result
    
    def calculate_duration_compliance(self, data):
        """计算时长达标度"""
        result = {}
        
        # 反应总时长
        reaction_time = data.get('反应总时长(秒)', 0)
        baseline_max_time = self.config['baseline_max_time']
        
        # 计算时长达标度
        if reaction_time >= baseline_max_time:
            # 超过基准时长，满分
            duration_score = 1.0
            extra_time = reaction_time - baseline_max_time
            result['时长评价'] = f'优秀(超出{extra_time:.0f}秒)'
        elif reaction_time >= baseline_max_time * 0.95:
            # 达到95%以上，良好
            duration_score = 0.8 + 0.2 * (reaction_time / baseline_max_time)
            result['时长评价'] = '良好'
        elif reaction_time >= baseline_max_time * 0.90:
            # 达到90%以上，合格
            duration_score = 0.6 + 0.2 * (reaction_time / baseline_max_time)
            result['时长评价'] = '合格'
        else:
            # 不足90%，不合格
            duration_score = reaction_time / baseline_max_time * 0.6
            shortage = baseline_max_time - reaction_time
            result['时长评价'] = f'不合格(短{shortage:.0f}秒)'
        
        result['时长达标度'] = round(duration_score, 3)
        result['反应总时长(秒)'] = round(reaction_time, 0)
        result['反应总时长(分钟)'] = round(reaction_time / 60, 1)
        result['时长达标率(%)'] = round(reaction_time / baseline_max_time * 100, 1)
        
        # 额外指标：启动和达峰性能
        startup_time = data.get('平均启动时长(秒)', 0)
        peak_time = data.get('平均达峰时长(秒)', 0)
        
        if startup_time > 0 and startup_time < 10:
            result['启动性能'] = '优秀'
        elif startup_time < 20:
            result['启动性能'] = '良好'
        else:
            result['启动性能'] = '需改进'
        
        result['启动时长(秒)'] = startup_time
        result['达峰时长(秒)'] = peak_time
        
        return result
    
    def calculate_temperature_safety(self, data):
        """计算温度安全度"""
        result = {}
        
        # 获取温度数据
        shell_temp = data.get('外壳最高温度(°C)', None)
        insulation_temp = data.get('隔热垫外最高温度(°C)', None)
        outlet_temp = data.get('供氧口最高温度(°C)', None)
        
        # 计算各部位温度得分
        shell_score = self.calc_temp_score(
            shell_temp, 
            self.config['thresholds']['shell_temp']
        )
        
        insulation_score = self.calc_temp_score(
            insulation_temp,
            self.config['thresholds']['insulation_temp']
        )
        
        outlet_score = self.calc_temp_score(
            outlet_temp,
            self.config['thresholds']['outlet_temp']
        )
        
        # 综合温度安全度（外壳最重要）
        temp_safety = (
            0.5 * shell_score +      # 外壳占50%
            0.3 * insulation_score + # 隔热垫占30%
            0.2 * outlet_score       # 供氧口占20%
        )
        
        result['温度安全度'] = round(temp_safety, 3)
        result['外壳温度得分'] = round(shell_score, 3)
        result['隔热垫温度得分'] = round(insulation_score, 3)
        result['供氧口温度得分'] = round(outlet_score, 3)
        
        # 记录实际温度
        if shell_temp is not None:
            result['外壳最高温度(°C)'] = shell_temp
        if insulation_temp is not None:
            result['隔热垫外最高温度(°C)'] = insulation_temp
        if outlet_temp is not None:
            result['供氧口最高温度(°C)'] = outlet_temp
        
        # 温度评价
        result['温度评价'] = self.get_level_evaluation(
            temp_safety,
            [0.9, 0.7, 0.5]
        )
        
        return result
    
    def calc_temp_score(self, temp, thresholds):
        """计算单个温度的得分"""
        if temp is None or pd.isna(temp):
            return 0.5  # 无数据时给中等分
        
        if isinstance(temp, str):
            if temp == '-' or temp == '':
                return 0.5
            try:
                temp = float(temp)
            except:
                return 0.5
        
        temp = float(temp)
        
        if temp <= thresholds['优秀']:
            return 1.0
        elif temp <= thresholds['良好']:
            return 0.8 + 0.2 * (thresholds['良好'] - temp) / (thresholds['良好'] - thresholds['优秀'])
        elif temp <= thresholds['合格']:
            return 0.6 + 0.2 * (thresholds['合格'] - temp) / (thresholds['合格'] - thresholds['良好'])
        elif temp <= thresholds['极限']:
            return 0.3 + 0.3 * (thresholds['极限'] - temp) / (thresholds['极限'] - thresholds['合格'])
        else:
            return 0.0
    
    def calculate_cv_score(self, cv_value):
        """计算CV值对应的得分"""
        if pd.isna(cv_value):
            return 0.5
        
        thresholds = self.config['thresholds']['cv_value']
        
        if cv_value <= thresholds['优秀']:
            return 1.0
        elif cv_value <= thresholds['良好']:
            return 0.8
        elif cv_value <= thresholds['合格']:
            return 0.6
        else:
            return 0.4
    
    def get_rating(self, score):
        """获取综合评级"""
        if score >= 0.90:
            return 'A级(优秀)'
        elif score >= 0.80:
            return 'B级(良好)'
        elif score >= 0.70:
            return 'C级(合格)'
        elif score >= 0.60:
            return 'D级(需改进)'
        else:
            return 'E级(不合格)'
    
    def get_level_evaluation(self, score, thresholds):
        """获取分级评价"""
        levels = ['优秀', '良好', '合格', '不合格']
        for i, threshold in enumerate(thresholds):
            if score >= threshold:
                return levels[i]
        return levels[-1]
    
    def identify_weaknesses(self, result):
        """识别不足之处"""
        weaknesses = []
        
        # 基准符合度问题
        if result['基准符合度'] < 0.85:
            if result['平均达标率(%)'] < 80:
                weaknesses.append(f"达标率偏低({result['平均达标率(%)']}%)")
            if result.get('360秒流量比', 1) < 0.9:
                weaknesses.append("前期产氧不足")
            if result.get('1200秒流量比', 1) < 0.9:
                weaknesses.append("后期产氧不足")
            if result.get('CV值', 0) > 0.1:
                weaknesses.append(f"流量稳定性差(CV={result.get('CV值', 0):.3f})")
        
        # 时长问题
        if result['时长达标度'] < 0.9:
            weaknesses.append(f"反应时长不足({result['时长达标率(%)']}%)")
        
        # 温度问题
        if result.get('外壳温度得分', 1) < 0.7:
            weaknesses.append(f"外壳温度过高({result.get('外壳最高温度(°C)', 'N/A')}°C)")
        if result.get('隔热垫温度得分', 1) < 0.7:
            weaknesses.append("隔热效果不佳")
        if result.get('供氧口温度得分', 1) < 0.7:
            weaknesses.append("供氧口温度过高")
        
        # 启动性能问题
        if result.get('启动性能') == '需改进':
            weaknesses.append(f"启动过慢({result.get('启动时长(秒)', 0)}秒)")
        
        return '; '.join(weaknesses) if weaknesses else '无明显不足'
    
    def identify_strengths(self, result):
        """识别优势特点"""
        strengths = []
        
        if result['基准符合度'] >= 0.95:
            strengths.append("流量控制优秀")
        if result['时长达标度'] >= 1.0:
            strengths.append("反应时长充足")
        if result['温度安全度'] >= 0.9:
            strengths.append("温度控制优秀")
        if result.get('总产氧量(L)', 0) >= 120:
            strengths.append("产氧量充足")
        if result.get('CV值', 1) < 0.05:
            strengths.append("稳定性极佳")
        if result.get('启动性能') == '优秀':
            strengths.append("快速启动")
        
        return '; '.join(strengths) if strengths else '表现均衡'
    
    def generate_recommendations(self, result):
        """生成改进建议"""
        recommendations = []
        
        # 基于达标率的建议
        if result['平均达标率(%)'] < 80:
            recommendations.append("增加主反应物含量或优化配方比例")
        elif result['平均达标率(%)'] < 90:
            recommendations.append("微调配方以提高产氧稳定性")
        
        # 基于时长的建议
        if result['时长达标率(%)'] < 95:
            recommendations.append("增加氧烛总长度或调整反应速率")
        
        # 基于温度的建议
        if result.get('外壳最高温度(°C)', 0) > 80:
            recommendations.append("改进隔热设计或降低反应剧烈程度")
        
        # 基于CV值的建议
        if result.get('CV值', 0) > 0.1:
            recommendations.append("改进混料均匀性和压制工艺")
        
        # 基于启动时间的建议
        if result.get('启动时长(秒)', 0) > 20:
            recommendations.append("增加点火药量或改进点火方式")
        
        # 基于流量比的建议
        if result.get('360秒流量比', 1) < 0.9:
            recommendations.append("优化A、B层配方，提高前期反应活性")
        if result.get('1200秒流量比', 1) < 0.9:
            recommendations.append("检查C3层配方，确保后期产氧充足")
        
        return recommendations if recommendations else ['产品性能良好，保持现有工艺']
    
    def evaluate_batch(self, df):
        """
        批量评价多个产品
        
        Parameters:
        df: DataFrame, 包含多个产品的数据
        
        Returns:
        DataFrame: 评价结果
        """
        results = []
        
        print("开始批量评价...")
        print("-" * 50)
        
        for idx, row in df.iterrows():
            try:
                # 将Series转换为字典
                product_data = row.to_dict()
                
                # 评价单个产品
                result = self.evaluate_product(product_data)
                results.append(result)
                
                print(f"✅ {result['产品编号']}: 综合得分 {result['综合得分']:.3f}, 评级 {result['评级']}")
                
            except Exception as e:
                print(f"❌ 评价第{idx}行数据时出错: {str(e)}")
        
        print("-" * 50)
        print(f"完成评价: {len(results)}/{len(df)} 个产品")
        
        return pd.DataFrame(results)
    
    def generate_comparison_report(self, results_df, output_file='产品评价对比报告.xlsx'):
        """生成对比报告"""
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # 1. 综合排名表
            ranking_df = results_df.sort_values('综合得分', ascending=False).reset_index(drop=True)
            ranking_df.index = ranking_df.index + 1  # 排名从1开始
            ranking_df.index.name = '排名'
            
            # 只显示关键列
            key_cols = [
                '产品编号', '配方代号', '工艺代号', '综合得分', '评级',
                '基准符合度', '时长达标度', '温度安全度',
                '平均达标率(%)', '反应总时长(分钟)', 
                '外壳最高温度(°C)', 'CV值',
                '不足之处', '优势特点'
            ]
            
            # 确保列存在
            display_cols = [col for col in key_cols if col in ranking_df.columns]
            ranking_df[display_cols].to_excel(writer, sheet_name='综合排名')
            
            # 2. 分类对比表
            # 按评级分组统计
            if '评级' in results_df.columns:
                grade_stats = results_df.groupby('评级').agg({
                    '综合得分': ['count', 'mean'],
                    '基准符合度': 'mean',
                    '时长达标度': 'mean',
                    '温度安全度': 'mean'
                }).round(3)
                
                grade_stats.columns = ['数量', '平均综合得分', '平均基准符合度', 
                                      '平均时长达标度', '平均温度安全度']
                grade_stats.to_excel(writer, sheet_name='评级统计')
            
            # 3. 最佳配方推荐
            top_n = min(10, len(results_df))
            best_df = ranking_df.head(top_n)[display_cols]
            best_df.to_excel(writer, sheet_name=f'TOP{top_n}推荐')
            
            # 4. 改进建议汇总
            if '改进建议' in results_df.columns:
                recommendations_data = []
                for idx, row in results_df.iterrows():
                    if isinstance(row['改进建议'], list):
                        for rec in row['改进建议']:
                            recommendations_data.append({
                                '产品编号': row['产品编号'],
                                '综合得分': row['综合得分'],
                                '改进建议': rec
                            })
                
                if recommendations_data:
                    rec_df = pd.DataFrame(recommendations_data)
                    rec_df.to_excel(writer, sheet_name='改进建议汇总', index=False)
            
            # 设置格式
            # 综合排名表格式
            worksheet1 = writer.sheets['综合排名']
            
            # 条件格式 - 综合得分
            if '综合得分' in display_cols:
                score_col = display_cols.index('综合得分') + 1  # 考虑索引列
                worksheet1.conditional_format(1, score_col, len(ranking_df), score_col, {
                    'type': '3_color_scale',
                    'min_color': '#FF0000',
                    'mid_color': '#FFFF00',
                    'max_color': '#00FF00'
                })
            
            # 达标率格式
            if '平均达标率(%)' in display_cols:
                rate_col = display_cols.index('平均达标率(%)') + 1
                worksheet1.conditional_format(1, rate_col, len(ranking_df), rate_col, {
                    'type': 'data_bar',
                    'bar_color': '#63C384'
                })
            
            # 设置列宽
            for worksheet in writer.sheets.values():
                worksheet.set_column('A:A', 8)   # 排名列
                worksheet.set_column('B:D', 15)  # 编号列
                worksheet.set_column('E:K', 12)  # 数值列
                worksheet.set_column('L:N', 30)  # 文本列
                
        print(f"\n✅ 评价报告已生成: {output_file}")
        self.print_summary(results_df)
    
    def print_summary(self, results_df):
        """打印汇总信息"""
        print("\n" + "=" * 60)
        print("评价汇总")
        print("=" * 60)
        print(f"评价产品数量: {len(results_df)}")
        print(f"平均综合得分: {results_df['综合得分'].mean():.3f}")
        print(f"最高分: {results_df['综合得分'].max():.3f}")
        print(f"最低分: {results_df['综合得分'].min():.3f}")
        
        print("\n评级分布:")
        grade_counts = results_df['评级'].value_counts()
        for grade, count in grade_counts.items():
            print(f"  {grade}: {count}个 ({count/len(results_df)*100:.1f}%)")
        
        # 找出最优配方
        if not results_df.empty:
            best_product = results_df.loc[results_df['综合得分'].idxmax()]
            print(f"\n最优产品:")
            print(f"  编号: {best_product['产品编号']}")
            print(f"  配方: {best_product.get('配方代号', 'N/A')}")
            print(f"  工艺: {best_product.get('工艺代号', 'N/A')}")
            print(f"  综合得分: {best_product['综合得分']}")
            print(f"  优势: {best_product.get('优势特点', 'N/A')}")
    
    def export_evaluation_results(self, results_df, export_dir='./exports'):
        """导出评价结果到多种格式"""
        os.makedirs(export_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Excel格式
        excel_file = os.path.join(export_dir, f'评价结果_{timestamp}.xlsx')
        self.generate_comparison_report(results_df, excel_file)
        
        # 2. CSV格式
        csv_file = os.path.join(export_dir, f'评价结果_{timestamp}.csv')
        results_df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        
        # 3. JSON格式
        json_file = os.path.join(export_dir, f'评价结果_{timestamp}.json')
        results_df.to_json(json_file, orient='records', force_ascii=False, indent=2)
        
        print(f"\n✅ 结果已导出到: {export_dir}")
        print(f"  - Excel: {os.path.basename(excel_file)}")
        print(f"  - CSV: {os.path.basename(csv_file)}")
        print(f"  - JSON: {os.path.basename(json_file)}")
        
        return excel_file


# 使用示例
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("氧烛产品评价系统")
    print("=" * 60)
    
    # 检查是否有输入文件
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = '横向对比数据汇总.xlsx'
    
    if not os.path.exists(input_file):
        print(f"❌ 文件不存在: {input_file}")
        print("请先运行数据提取模块生成汇总数据")
        sys.exit(1)
    
    # 读取数据
    print(f"\n读取数据文件: {input_file}")
    df = pd.read_excel(input_file, sheet_name='数据汇总')
    print(f"✅ 读取 {len(df)} 条数据")
    
    # 创建评价器
    config_file = './data/config.json'
    evaluator = OxygenCandleEvaluator(config_file)
    
    # 批量评价
    print("\n开始评价...")
    results = evaluator.evaluate_batch(df)
    
    # 生成报告
    if not results.empty:
        output_file = '产品评价对比报告.xlsx'
        evaluator.generate_comparison_report(results, output_file)
        
        # 导出多种格式
        evaluator.export_evaluation_results(results)
    else:
        print("❌ 评价失败，未生成结果")