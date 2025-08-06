#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评分和排名 - 最新版
根据春娟的要求调整评分规则
"""

import pandas as pd
import numpy as np
import os

print("=" * 60)
print("        🏆 样品评分和排名 - 最新版")
print("=" * 60)

# 读取当前会话的时间戳
try:
    with open('./reports_output/current_session.txt', 'r') as f:
        timestamp = f.read().strip()
    output_dir = f"./reports_output/{timestamp}"
except:
    output_dir = "./reports_output"

print(f"📁 使用输出文件夹: {output_dir}")

# 读取数据
input_file = os.path.join(output_dir, "样品分析汇总.xlsx")
if not os.path.exists(input_file):
    print("❌ 请先运行'简单分析程序_改进版.py'")
    exit()

print("读取数据...")
df = pd.read_excel(input_file)
print(f"✅ 读取 {len(df)} 个样品数据")

# 数据清洗函数
def clean_number(value, default=0):
    if pd.isna(value) or value == '-' or value == '读取失败':
        return default
    try:
        return float(value)
    except:
        return default

print("\n开始评分...")
print("-" * 60)

# ========== 最新评分体系 ==========
# 总分100分，分配如下：
# 1. 达标率: 50分
# 2. 累计流量: 不打分（仅展示）
# 3. 产氧时间: 10分（≥22分钟才得分，越长越好）
# 4. 启动时长: 10分（≤1秒满分）
# 5. 达峰时长: 10分（≤10秒满分）
# 6. 异常扣分: 10分（无异常满分）
# 7. 温度: 10分（温度越低越好）

# 1. 达标率得分（50分）
df['达标率_数值'] = df['达标率(%)'].apply(lambda x: clean_number(x))
df['达标率得分'] = df['达标率_数值'] * 0.5

# 2. 累计流量（不打分，仅保留数值）
df['累计流量_数值'] = df['累计流量(升)'].apply(lambda x: clean_number(x))

# 3. 产氧时间得分（10分）- 小于22分钟得0分，越长越好
df['产氧时间_数值'] = df['产氧时间(分钟)'].apply(lambda x: clean_number(x))
def calc_time_score(time_minutes):
    if time_minutes < 22:
        return 0
    elif time_minutes >= 30:  # 30分钟及以上满分
        return 10
    else:
        # 22-30分钟之间，线性增长
        return (time_minutes - 22) / 8 * 10

df['时间得分'] = df['产氧时间_数值'].apply(calc_time_score)

# 4. 启动时长得分（10分）- ≤1秒满分
df['启动时长_数值'] = df['启动时长(秒)'].apply(lambda x: clean_number(x, 999))
df['启动得分'] = df['启动时长_数值'].apply(
    lambda x: 10 if x <= 1 else max(0, 10 - (x-1)*2)  # 每多1秒扣2分
)

# 5. 达峰时长得分（10分）- ≤10秒满分
df['达峰时长_数值'] = df['达峰时长(秒)'].apply(lambda x: clean_number(x, 999))
df['达峰得分'] = df['达峰时长_数值'].apply(
    lambda x: 10 if x <= 10 else max(0, 10 - (x-10)*0.5)  # 每多1秒扣0.5分
)

# 6. 异常扣分（10分基础分）
df['异常次数_数值'] = df['异常次数'].apply(lambda x: clean_number(x))
df['异常时间_数值'] = df['异常持续时间(秒)'].apply(lambda x: clean_number(x))
df['流量差异_数值'] = df['流量差异'].apply(lambda x: clean_number(x))

# 异常得分：基础10分，扣分规则：
# - 每个异常扣1分
# - 每10秒异常时间扣1分
# - 流量差异每0.1扣1分
df['异常得分'] = 10 - df['异常次数_数值'] - df['异常时间_数值']/10 - df['流量差异_数值']*10
df['异常得分'] = df['异常得分'].apply(lambda x: max(0, x))  # 不能为负

# 7. 温度得分（10分）
df['外壳温度_数值'] = df['外壳最高温度(°C)'].apply(lambda x: clean_number(x, 999))
df['隔热温度_数值'] = df['隔热垫外最高温度(°C)'].apply(lambda x: clean_number(x, 999))
df['供氧温度_数值'] = df['供氧口最高温度(°C)'].apply(lambda x: clean_number(x, 999))

# 最新温度评分规则：
# 外壳: ≤275°C满分，每高10°C扣1分（权重4分）
# 隔热垫: ≤150°C满分，每高10°C扣1分（权重3分）
# 供氧口: ≤50°C满分，每高10°C扣1分（权重3分）
def calc_temp_score(shell, insulation, outlet):
    shell_score = 4 if shell <= 275 else max(0, 4 - (shell-275)/10)
    insulation_score = 3 if insulation <= 150 else max(0, 3 - (insulation-150)/10)
    outlet_score = 3 if outlet <= 50 else max(0, 3 - (outlet-50)/10)
    return shell_score + insulation_score + outlet_score

df['温度得分'] = df.apply(
    lambda row: calc_temp_score(row['外壳温度_数值'], row['隔热温度_数值'], row['供氧温度_数值']),
    axis=1
)

# 8. 综合得分
df['综合得分'] = (
    df['达标率得分'] + 
    df['时间得分'] + 
    df['启动得分'] + 
    df['达峰得分'] + 
    df['异常得分'] + 
    df['温度得分']
)

# 9. 评级
def get_grade(score):
    if score >= 90:
        return 'A级(优秀)'
    elif score >= 80:
        return 'B级(良好)'
    elif score >= 70:
        return 'C级(合格)'
    elif score >= 60:
        return 'D级(及格)'
    else:
        return 'E级(需改进)'

df['评级'] = df['综合得分'].apply(get_grade)
df['排名'] = df['综合得分'].rank(ascending=False, method='min').astype(int)

# 按得分排序
df_sorted = df.sort_values('综合得分', ascending=False)

# 选择要显示的列（包含累计流量但不参与评分）
display_columns = [
    '排名', '样品编号', '温度等级',
    '达标率(%)', '累计流量(升)', '产氧时间(分钟)',
    '启动时长(秒)', '达峰时长(秒)',
    '异常次数', '外壳最高温度(°C)',
    '综合得分', '评级'
]

display_columns = [col for col in display_columns if col in df_sorted.columns]
result_df = df_sorted[display_columns].reset_index(drop=True)

# 保存结果
output_file = os.path.join(output_dir, "样品评分排名.xlsx")
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    # 主排名表
    result_df.to_excel(writer, sheet_name='排名表', index=False)
    
    # 分组统计
    stats_df = df.groupby('温度等级')['综合得分'].agg(['count', 'mean', 'max', 'min']).round(2)
    stats_df.columns = ['样品数', '平均分', '最高分', '最低分']
    stats_df.to_excel(writer, sheet_name='分组统计')
    
    # 详细得分表（不包含流量得分）
    score_details = df_sorted[[
        '样品编号', '达标率得分', '时间得分',
        '启动得分', '达峰得分', '异常得分', '温度得分', '综合得分'
    ]].round(2)
    score_details.to_excel(writer, sheet_name='得分明细', index=False)

print("✅ 评分完成！")

# 显示评分权重
print("\n" + "=" * 60)
print("📊 最新评分体系（满分100）：")
print("-" * 60)
print("  达标率: 50分")
print("  累计流量: 不计分（仅展示）")
print("  产氧时间: 10分（≥22分钟才得分，越长越好）")
print("  启动时长: 10分（≤1秒满分）")
print("  达峰时长: 10分（≤10秒满分）")
print("  异常扣分: 10分（无异常满分）")
print("  温度: 10分")
print("    - 外壳≤275°C满分(4分)")
print("    - 隔热垫≤150°C满分(3分)")
print("    - 供氧口≤50°C满分(3分)")

print("\n" + "=" * 60)
print("📊 排名前5的样品：")
print("-" * 60)

for idx, row in result_df.head(5).iterrows():
    print(f"{row['排名']}. {row['样品编号']} - {row['综合得分']:.1f}分 ({row['评级']})")
    print(f"   达标率:{row.get('达标率(%)', 0):.1f}% 时间:{row.get('产氧时间(分钟)', 0):.1f}分钟")
    print(f"   启动:{row.get('启动时长(秒)', 0):.1f}秒 异常:{row.get('异常次数', 0)}次")
    print(f"   外壳温度:{row.get('外壳最高温度(°C)', 0):.0f}°C")

# 分析得分分布
print("\n" + "=" * 60)
print("📊 各项得分统计：")
print("-" * 60)
print(f"  达标率平均得分: {df['达标率得分'].mean():.1f}/50分")
print(f"  产氧时间平均得分: {df['时间得分'].mean():.1f}/10分")
print(f"  启动时长平均得分: {df['启动得分'].mean():.1f}/10分")
print(f"  达峰时长平均得分: {df['达峰得分'].mean():.1f}/10分")
print(f"  异常平均得分: {df['异常得分'].mean():.1f}/10分")
print(f"  温度平均得分: {df['温度得分'].mean():.1f}/10分")

print("\n" + "=" * 60)
print(f"🎉 完成！结果已保存到: {output_file}")
print("=" * 60)
