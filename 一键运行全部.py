#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键运行所有分析步骤
兼容Windows和Mac
"""

import os
import sys
import subprocess
import time
from datetime import datetime

print("=" * 60)
print("        🚀 一键运行全部分析")
print("=" * 60)

# 显示时间
current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
print(f"📅 运行时间: {current_time}")
print("-" * 60)

# 使用sys.executable确保使用正确的Python解释器
python_exe = sys.executable

# 步骤1：基础分析
print("\n[1/4] 运行基础分析...")
subprocess.run([python_exe, "简单分析程序.py"])
time.sleep(1)

# 步骤2：评分排名
print("\n[2/4] 运行评分排名...")
subprocess.run([python_exe, "评分排名程序.py"])
time.sleep(1)

# 步骤3：对比分析
print("\n[3/4] 运行对比分析...")
subprocess.run([python_exe, "对比分析程序.py"])
time.sleep(1)

# 显示结果文件夹
try:
    with open('./reports_output/current_session.txt', 'r') as f:
        timestamp = f.read().strip()
    print("\n" + "=" * 60)
    print(f"✅ 所有结果已保存在: reports_output/{timestamp}/")
    print("包含文件：")
    print("  - 样品分析汇总.xlsx")
    print("  - 样品评分排名.xlsx")
    print("  - 分析图表.png")
    print("=" * 60)
except:
    print("\n" + "=" * 60)
    print(f"✅ 所有结果已保存在: reports_output/")
    print("=" * 60)

# 步骤4：启动Web系统
print("\n[4/4] 启动Web系统...")
print("-" * 60)
print("🌐 浏览器将自动打开")
print("🌐 如未打开，请访问: http://localhost:8501")
print("🌐 按 Ctrl+C 停止系统")
print("-" * 60)

# Windows下暂停，让用户看到结果
if sys.platform == 'win32':
    input("\n按回车键继续启动Web系统...")

subprocess.run([python_exe, "-m", "streamlit", "run", "网页系统.py"])
