#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
氧烛分析系统 - 独立版本
所有功能集成在一个文件中
"""

import os
import sys
import traceback
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

def setup_environment():
    """设置运行环境"""
    if getattr(sys, 'frozen', False):
        # 打包后的exe
        application_path = os.path.dirname(sys.executable)
    else:
        # 开发环境
        application_path = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(application_path)
    
    # 创建必要的目录
    for folder in ['reports_input', 'reports_output', 'data']:
        if not os.path.exists(folder):
            os.makedirs(folder)
    
    return application_path

def run_simple_analysis():
    """数据提取功能"""
    print("\n" + "="*60)
    print("开始数据提取...")
    print("="*60)
    
    input_dir = "reports_input"
    output_dir = "reports_output"
    
    # 获取所有产品文件夹
    folders = [f for f in os.listdir(input_dir) 
               if os.path.isdir(os.path.join(input_dir, f))]
    
    if not folders:
        print("❌ 未找到产品文件夹")
        print(f"请将测试报告放入 {input_dir} 目录")
        return False
    
    print(f"找到 {len(folders)} 个产品文件夹")
    
    results = []
    for folder in folders:
        print(f"\n处理: {folder}")
        folder_path = os.path.join(input_dir, folder)
        
        # 查找Excel文件
        excel_files = [f for f in os.listdir(folder_path) 
                       if f.endswith(('.xlsx', '.xls'))]
        
        if not excel_files:
            print(f"  ⚠️ 未找到Excel文件")
            continue
        
        for excel_file in excel_files:
            file_path = os.path.join(folder_path, excel_file)
            try:
                # 读取Excel文件
                xls = pd.ExcelFile(file_path)
                
                # 查找原始数据sheet
                data_sheet = None
                for sheet in xls.sheet_names:
                    if '原始数据' in sheet or '数据' in sheet:
                        data_sheet = sheet
                        break
                
                if data_sheet:
                    df = pd.read_excel(file_path, sheet_name=data_sheet)
                    print(f"  ✓ 读取 {excel_file}")
                    
                    # 简单分析
                    if '平均流量L/Min' in df.columns:
                        avg_flow = df['平均流量L/Min'].mean()
                        max_flow = df['平均流量L/Min'].max()
                        
                        results.append({
                            '产品编号': folder,
                            '平均流量': round(avg_flow, 2),
                            '最大流量': round(max_flow, 2),
                            '数据点数': len(df)
                        })
                        
                        print(f"    平均流量: {avg_flow:.2f} L/min")
                        print(f"    最大流量: {max_flow:.2f} L/min")
                
            except Exception as e:
                print(f"  ❌ 处理失败: {e}")
    
    # 保存结果
    if results:
        result_df = pd.DataFrame(results)
        
        # 创建时间戳文件夹
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = os.path.join(output_dir, timestamp)
        os.makedirs(output_path, exist_ok=True)
        
        # 保存Excel
        output_file = os.path.join(output_path, "分析结果.xlsx")
        result_df.to_excel(output_file, index=False)
        
        print(f"\n✅ 结果保存到: {output_file}")
        return True
    else:
        print("\n❌ 没有成功处理任何文件")
        return False

def run_ranking_analysis():
    """评分排名功能"""
    print("\n" + "="*60)
    print("开始评分排名...")
    print("="*60)
    
    # 查找最新的分析结果
    output_dir = "reports_output"
    folders = [f for f in os.listdir(output_dir) 
               if os.path.isdir(os.path.join(output_dir, f))]
    
    if not folders:
        print("❌ 未找到分析结果")
        return False
    
    folders.sort()
    latest_folder = folders[-1]
    result_file = os.path.join(output_dir, latest_folder, "分析结果.xlsx")
    
    if os.path.exists(result_file):
        df = pd.read_excel(result_file)
        
        # 简单评分（示例）
        df['得分'] = df['平均流量'] * 10 + df['最大流量'] * 5
        df['排名'] = df['得分'].rank(ascending=False, method='min').astype(int)
        df = df.sort_values('排名')
        
        # 保存排名结果
        ranking_file = os.path.join(output_dir, latest_folder, "排名结果.xlsx")
        df.to_excel(ranking_file, index=False)
        
        print(f"\n排名结果:")
        print(df[['排名', '产品编号', '得分']].head(10))
        print(f"\n✅ 结果保存到: {ranking_file}")
        return True
    else:
        print("❌ 未找到分析结果文件")
        return False

def main():
    """主程序"""
    print("=" * 60)
    print("     氧烛产品分析系统 v1.0")
    print("=" * 60)
    
    # 设置环境
    app_path = setup_environment()
    print(f"\n工作目录: {app_path}")
    
    while True:
        print("\n" + "=" * 60)
        print("请选择功能：")
        print("1. 运行完整分析")
        print("2. 数据提取")
        print("3. 评分排名")
        print("4. 查看说明")
        print("0. 退出")
        print("=" * 60)
        
        choice = input("\n请输入选项 (0-4): ").strip()
        
        if choice == '0':
            print("\n退出程序")
            break
        elif choice == '1':
            # 完整分析
            if run_simple_analysis():
                run_ranking_analysis()
        elif choice == '2':
            run_simple_analysis()
        elif choice == '3':
            run_ranking_analysis()
        elif choice == '4':
            print("\n使用说明：")
            print("1. 将测试报告放入 reports_input 文件夹")
            print("2. 每个产品创建一个子文件夹")
            print("3. 运行分析功能")
            print("4. 结果保存在 reports_output 文件夹")
        else:
            print("无效选项")
    
    print("\n按回车键退出...")
    input()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
        traceback.print_exc()
        print("\n按回车键退出...")
        input()
