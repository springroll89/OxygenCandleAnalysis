#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比分析TOP样品和可视化 - 修复版
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # Mac系统
plt.rcParams['axes.unicode_minus'] = False

print("=" * 60)
print("        📈 样品对比分析")
print("=" * 60)

# 读取当前会话的时间戳
try:
    with open('./reports_output/current_session.txt', 'r') as f:
        timestamp = f.read().strip()
    output_dir = f"./reports_output/{timestamp}"
except:
    output_dir = "./reports_output"

print(f"📁 使用输出文件夹: {output_dir}")

# 读取排名数据
ranking_file = os.path.join(output_dir, "样品评分排名.xlsx")
df = pd.read_excel(ranking_file, sheet_name='排名表')
stats = pd.read_excel(ranking_file, sheet_name='分组统计')

print(f"读取 {len(df)} 个样品数据")

# 创建图表（2x2布局）
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle(f'氧烛样品分析报告 - {timestamp}', fontsize=16, fontweight='bold')

# 图1：TOP10样品得分对比
ax1 = axes[0, 0]
top10 = df.head(10)

# 根据温度等级着色（修正版）
colors = []
for temp in top10['温度等级']:
    if temp == '常温' or 'MT' in str(temp):  # 兼容常温和MT
        colors.append('#FF6B6B')
    elif temp == '低温' or 'LT' in str(temp):
        colors.append('#4ECDC4')
    elif temp == '高温' or 'HT' in str(temp):
        colors.append('#45B7D1')
    else:  # 未注明或标准
        colors.append('#96CEB4')

bars = ax1.bar(range(len(top10)), top10['综合得分'], color=colors)
ax1.set_xticks(range(len(top10)))
ax1.set_xticklabels(top10['样品编号'], rotation=45, ha='right')
ax1.set_ylabel('综合得分')
ax1.set_title('TOP10 样品排名')
ax1.grid(axis='y', alpha=0.3)

for i, (bar, score) in enumerate(zip(bars, top10['综合得分'])):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
             f'{score:.1f}', ha='center', va='bottom', fontsize=9)

# 图2：温度等级平均分对比
ax2 = axes[0, 1]
# 更新温度等级列表
temp_levels = ['未注明', '低温', '常温', '高温']
avg_scores = []
for temp in temp_levels:
    temp_df = df[df['温度等级'] == temp]
    avg_scores.append(temp_df['综合得分'].mean() if len(temp_df) > 0 else 0)

colors2 = ['#96CEB4', '#4ECDC4', '#FF6B6B', '#45B7D1']
bars2 = ax2.bar(temp_levels, avg_scores, color=colors2)
ax2.set_ylabel('平均得分')
ax2.set_title('各温度等级平均得分')
ax2.grid(axis='y', alpha=0.3)

for bar, score in zip(bars2, avg_scores):
    if score > 0:  # 只显示有数据的
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                 f'{score:.1f}', ha='center', va='bottom')

# 图3：达标率分布
ax3 = axes[1, 0]
def clean_value(x):
    if pd.isna(x) or x == '-' or x == '读取失败':
        return 0
    try:
        return float(x)
    except:
        return 0

df['达标率_clean'] = df['达标率(%)'].apply(clean_value)
temp_data = []
for temp in temp_levels:
    temp_df = df[df['温度等级'] == temp]
    if len(temp_df) > 0:
        temp_data.append(temp_df['达标率_clean'].values)
    else:
        temp_data.append([0])

# 只绘制有数据的箱线图
valid_data = [(d, l, c) for d, l, c in zip(temp_data, temp_levels, colors2) if len(d) > 0 and any(d)]
if valid_data:
    bp = ax3.boxplot([d[0] for d in valid_data], labels=[d[1] for d in valid_data], patch_artist=True)
    for patch, (_, _, color) in zip(bp['boxes'], valid_data):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

ax3.set_ylabel('达标率 (%)')
ax3.set_title('各温度等级达标率分布')
ax3.grid(axis='y', alpha=0.3)

# 图4：样品数量统计
ax4 = axes[1, 1]
counts = [len(df[df['温度等级'] == temp]) for temp in temp_levels]
# 过滤掉数量为0的
valid_temps = [(t, c, col) for t, c, col in zip(temp_levels, counts, colors2) if c > 0]
if valid_temps:
    wedges, texts, autotexts = ax4.pie(
        [c for _, c, _ in valid_temps], 
        labels=[t for t, _, _ in valid_temps],
        colors=[col for _, _, col in valid_temps],
        autopct='%1.0f%%', 
        startangle=90
    )
ax4.set_title(f'样品温度等级分布 (总计{len(df)}个)')

plt.tight_layout()

# 保存图表
output_image = os.path.join(output_dir, "分析图表.png")
plt.savefig(output_image, dpi=150, bbox_inches='tight')
print(f"\n✅ 图表已保存: {output_image}")
plt.show()

print("\n" + "=" * 60)
print(f"🎉 分析完成！所有文件保存在: {output_dir}")
print("=" * 60)
