#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
氧烛数据分析程序 - 改进版（修复异常分析）
增加更多评价指标
"""

import os
import pandas as pd
import numpy as np
import glob
from datetime import datetime

print("=" * 60)
print("        🔥 氧烛数据分析程序 - 改进版")
print("=" * 60)

# 创建时间戳文件夹
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = f"./reports_output/{timestamp}"
os.makedirs(output_dir, exist_ok=True)

# 保存时间戳
with open('./reports_output/current_session.txt', 'w') as f:
    f.write(timestamp)

print(f"📁 输出文件夹: {output_dir}")
print("-" * 60)

input_dir = "./reports_input"

# 获取所有样品文件夹
sample_folders = os.listdir(input_dir)
sample_folders = [f for f in sample_folders if os.path.isdir(os.path.join(input_dir, f))]
sample_folders.sort()

print(f"\n找到 {len(sample_folders)} 个样品")
print("-" * 60)

all_data = []

# 处理每个样品
for i, folder in enumerate(sample_folders, 1):
    print(f"\n[{i}/{len(sample_folders)}] 处理样品: {folder}")
    
    folder_path = os.path.join(input_dir, folder)
    
    # 查找文件
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    report_files = glob.glob(os.path.join(folder_path, "*_分析报告.xlsx"))
    
    sample_data = {
        '样品编号': folder,
        '温度文件': '有' if csv_files else '无',
        '分析报告': '有' if report_files else '无'
    }
    
    # 判断温度等级（改进版）
    if 'MT' in folder or '(MT)' in folder:
        sample_data['温度等级'] = '常温'  # MT改为常温
    elif 'LT' in folder or '(LT)' in folder:
        sample_data['温度等级'] = '低温'
    elif 'HT' in folder or '(HT)' in folder:
        sample_data['温度等级'] = '高温'
    else:
        sample_data['温度等级'] = '未注明'  # 其他改为未注明
    
    # 如果有分析报告，提取所有数据
    if report_files:
        report_file = report_files[0]
        try:
            # 1. 读取性能指标分析
            try:
                perf_df = pd.read_excel(report_file, sheet_name='性能指标分析')
                
                # 统计传感器数量（非平均值行的数量）
                sensor_rows = perf_df[~perf_df['设备'].astype(str).str.contains('平均', na=False)]
                sensor_count = len(sensor_rows)
                sample_data['传感器数量'] = sensor_count
                
                # 查找平均值行
                avg_row = perf_df[perf_df['设备'].astype(str).str.contains('平均', na=False)]
                if not avg_row.empty:
                    row = avg_row.iloc[0]
                    
                    # 基础指标
                    sample_data['达标率(%)'] = row.get('达标率(%)', 0)
                    
                    # 累计流量 = 平均值 × 传感器数量
                    avg_flow = float(row.get('累计流量(升)', 0))
                    sample_data['平均流量(升)'] = avg_flow
                    sample_data['累计流量(升)'] = avg_flow * sensor_count
                    
                    sample_data['产氧时间(分钟)'] = row.get('产氧时间(分钟)', 0)
                    
                    # 新增：启动时长和达峰时长
                    sample_data['启动时长(秒)'] = row.get('启动时长(秒)', 0)
                    sample_data['达峰时长(秒)'] = row.get('达峰时长(秒)', 0)
                    
                    print(f"  ✅ 达标率: {sample_data['达标率(%)']}%")
                    print(f"  ✅ 累计流量: {sample_data['累计流量(升)']:.1f}升 ({sensor_count}个传感器)")
                    print(f"  ✅ 启动时长: {sample_data['启动时长(秒)']}秒")
            except Exception as e:
                print(f"  ⚠️ 读取性能指标失败: {e}")
                sample_data['达标率(%)'] = 0
                sample_data['累计流量(升)'] = 0
                sample_data['产氧时间(分钟)'] = 0
                sample_data['启动时长(秒)'] = 999
                sample_data['达峰时长(秒)'] = 999
            
            # 2. 读取综合异常分析 - 【全新修复版】
            try:
                anomaly_df = pd.read_excel(report_file, sheet_name='综合异常分析')
                
                # 初始化默认值
                sample_data['异常次数'] = 0
                sample_data['异常持续时间(秒)'] = 0
                sample_data['流量差异'] = 0
                
                # 查找"平均值异常分析"标题的位置
                avg_title_row = None
                for idx, row in anomaly_df.iterrows():
                    # 检查第一列是否包含"平均值异常分析"
                    first_col_value = str(anomaly_df.iloc[idx, 0])
                    if '平均值异常分析' in first_col_value or '平均值' in first_col_value:
                        avg_title_row = idx
                        print(f"  📊 找到'平均值异常分析'标题在第{idx}行")
                        break
                
                if avg_title_row is not None:
                    # 获取平均值异常分析部分的数据
                    # 跳过标题行，从下一行开始读取数据
                    data_start_row = avg_title_row + 2  # 跳过标题和列名行
                    
                    # 收集所有有效数据行
                    total_duration = 0
                    total_flow_diff = 0
                    anomaly_count = 0
                    
                    # 从data_start_row开始读取，直到遇到空行或表格结束
                    for idx in range(data_start_row, len(anomaly_df)):
                        row = anomaly_df.iloc[idx]
                        
                        # 检查是否是有效数据行（至少有一个非空值）
                        if row.isna().all():
                            break  # 遇到全空行，结束
                        
                        # 检查第一列是否是数字（开始时间）
                        try:
                            first_val = float(row.iloc[0])
                            # 这是一个有效的异常数据行
                            anomaly_count += 1
                            
                            # 累加持续时间（第3列，索引2）
                            if pd.notna(row.iloc[2]):
                                duration = float(row.iloc[2])
                                total_duration += duration
                            
                            # 累加流量差异（第4列，索引3）
                            if pd.notna(row.iloc[3]):
                                flow_diff = float(row.iloc[3])
                                total_flow_diff += abs(flow_diff)  # 取绝对值
                                
                        except (ValueError, TypeError):
                            # 如果第一列不是数字，可能是另一个标题，停止
                            if pd.notna(row.iloc[0]) and any(keyword in str(row.iloc[0]) for keyword in ['分析', '号', '总计']):
                                break
                            continue
                    
                    # 设置结果
                    sample_data['异常次数'] = anomaly_count
                    sample_data['异常持续时间(秒)'] = round(total_duration, 2)
                    sample_data['流量差异'] = round(total_flow_diff, 3)
                    
                    if anomaly_count > 0:
                        print(f"  ✅ 异常次数: {anomaly_count}")
                        print(f"     持续时间总和: {total_duration:.2f}秒")
                        print(f"     流量差异总和: {total_flow_diff:.3f}")
                else:
                    print(f"  ⚠️ 未找到'平均值异常分析'部分")
                    
            except Exception as e:
                print(f"  ⚠️ 读取异常分析失败: {e}")
                import traceback
                traceback.print_exc()
                sample_data['异常次数'] = 0
                sample_data['异常持续时间(秒)'] = 0
                sample_data['流量差异'] = 0
            
            # 3. 读取点火测试记录数据（温度）
            try:
                ignition_df = pd.read_excel(report_file, sheet_name='点火测试记录数据')
                
                # 查找总计行
                total_row = ignition_df[ignition_df['传感器'].astype(str).str.contains('总计', na=False)]
                if not total_row.empty:
                    row = total_row.iloc[0]
                    sample_data['外壳最高温度(°C)'] = float(row.get('外壳最高温度(°C)', 999))
                    sample_data['隔热垫外最高温度(°C)'] = float(row.get('隔热垫外最高温度(°C)', 999))
                    sample_data['供氧口最高温度(°C)'] = float(row.get('供氧口最高温度(°C)', 999))
                    print(f"  ✅ 外壳温度: {sample_data['外壳最高温度(°C)']}°C")
                else:
                    sample_data['外壳最高温度(°C)'] = 999
                    sample_data['隔热垫外最高温度(°C)'] = 999
                    sample_data['供氧口最高温度(°C)'] = 999
            except Exception as e:
                print(f"  ⚠️ 读取温度数据失败: {e}")
                sample_data['外壳最高温度(°C)'] = 999
                sample_data['隔热垫外最高温度(°C)'] = 999
                sample_data['供氧口最高温度(°C)'] = 999
                
        except Exception as e:
            print(f"  ❌ 读取报告总体失败: {e}")
            # 设置默认值
            sample_data.update({
                '达标率(%)': 0,
                '累计流量(升)': 0,
                '产氧时间(分钟)': 0,
                '启动时长(秒)': 999,
                '达峰时长(秒)': 999,
                '异常次数': 0,
                '异常持续时间(秒)': 0,
                '流量差异': 0,
                '外壳最高温度(°C)': 999,
                '隔热垫外最高温度(°C)': 999,
                '供氧口最高温度(°C)': 999
            })
    
    all_data.append(sample_data)

# 创建汇总表
print("\n" + "=" * 60)
print("生成汇总报告...")

summary_df = pd.DataFrame(all_data)

# 保存到Excel
output_file = os.path.join(output_dir, "样品分析汇总.xlsx")
summary_df.to_excel(output_file, index=False)

print(f"✅ 汇总报告已保存: {output_file}")
print("\n汇总统计：")
print(f"  - 总样品数: {len(summary_df)}")
print(f"  - 未注明: {len(summary_df[summary_df['温度等级']=='未注明'])} 个")
print(f"  - 低温(LT): {len(summary_df[summary_df['温度等级']=='低温'])} 个")
print(f"  - 常温(MT): {len(summary_df[summary_df['温度等级']=='常温'])} 个")
print(f"  - 高温(HT): {len(summary_df[summary_df['温度等级']=='高温'])} 个")

# 显示异常统计
if '异常次数' in summary_df.columns:
    valid_anomalies = summary_df[summary_df['异常次数'] > 0]
    print(f"\n异常统计：")
    print(f"  - 有异常的样品数: {len(valid_anomalies)} 个")
    if len(valid_anomalies) > 0:
        print(f"  - 平均异常次数: {valid_anomalies['异常次数'].mean():.1f}")
        print(f"  - 最大异常次数: {valid_anomalies['异常次数'].max()}")

print("\n" + "=" * 60)
print("🎉 分析完成！")
print(f"📁 结果保存在: {output_dir}")
print("=" * 60)