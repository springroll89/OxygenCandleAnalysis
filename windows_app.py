#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
氧烛分析系统 - Windows独立版
所有功能集成，无需外部依赖文件
"""

import os
import sys
import json
import traceback
from datetime import datetime
from pathlib import Path

# 基础导入
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("警告: pandas未安装，部分功能受限")

def create_test_data():
    """创建测试数据用于演示"""
    test_dir = "reports_input/示例产品"
    os.makedirs(test_dir, exist_ok=True)
    
    if PANDAS_AVAILABLE:
        # 创建示例Excel文件
        data = {
            '时间(s)': list(range(0, 1200, 10)),
            '平均流量L/Min': [2.5 + np.sin(i/100) * 0.5 for i in range(120)],
            '温度': [20 + i * 0.1 for i in range(120)]
        }
        df = pd.DataFrame(data)
        df.to_excel(f"{test_dir}/测试数据.xlsx", sheet_name="原始数据", index=False)
        print(f"✓ 创建示例数据: {test_dir}/测试数据.xlsx")
    else:
        # 创建文本说明文件
        with open(f"{test_dir}/说明.txt", "w", encoding="utf-8") as f:
            f.write("请将Excel测试报告放入此文件夹\n")
            f.write("Excel文件应包含'原始数据'工作表\n")
        print(f"✓ 创建说明文件: {test_dir}/说明.txt")

def simple_analysis():
    """简单的数据分析（不依赖复杂模块）"""
    print("\n" + "="*60)
    print("执行数据分析...")
    print("="*60)
    
    input_dir = "reports_input"
    output_dir = "reports_output"
    
    # 确保目录存在
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有子文件夹
    try:
        folders = [f for f in os.listdir(input_dir) 
                  if os.path.isdir(os.path.join(input_dir, f))]
    except Exception as e:
        print(f"❌ 读取目录失败: {e}")
        return False
    
    if not folders:
        print(f"⚠️ {input_dir} 目录为空")
        print("创建示例数据...")
        create_test_data()
        folders = [f for f in os.listdir(input_dir) 
                  if os.path.isdir(os.path.join(input_dir, f))]
    
    print(f"找到 {len(folders)} 个产品文件夹:")
    for folder in folders:
        print(f"  - {folder}")
    
    # 分析每个文件夹
    results = []
    for folder in folders:
        folder_path = os.path.join(input_dir, folder)
        print(f"\n处理: {folder}")
        
        # 查找Excel文件
        excel_files = []
        try:
            for file in os.listdir(folder_path):
                if file.endswith(('.xlsx', '.xls')):
                    excel_files.append(file)
        except Exception as e:
            print(f"  ❌ 读取文件失败: {e}")
            continue
        
        if not excel_files:
            print(f"  ⚠️ 未找到Excel文件")
            continue
        
        for excel_file in excel_files:
            file_path = os.path.join(folder_path, excel_file)
            print(f"  分析文件: {excel_file}")
            
            if PANDAS_AVAILABLE:
                try:
                    # 使用pandas读取
                    df = pd.read_excel(file_path, sheet_name=0)
                    
                    # 查找流量列
                    flow_col = None
                    for col in df.columns:
                        if '流量' in str(col) or 'flow' in str(col).lower():
                            flow_col = col
                            break
                    
                    if flow_col:
                        avg_flow = df[flow_col].mean()
                        max_flow = df[flow_col].max()
                        min_flow = df[flow_col].min()
                        
                        results.append({
                            '产品': folder,
                            '文件': excel_file,
                            '平均流量': round(avg_flow, 2),
                            '最大流量': round(max_flow, 2),
                            '最小流量': round(min_flow, 2),
                            '数据点': len(df)
                        })
                        
                        print(f"    ✓ 平均流量: {avg_flow:.2f} L/min")
                        print(f"    ✓ 最大流量: {max_flow:.2f} L/min")
                    else:
                        print(f"    ⚠️ 未找到流量数据列")
                        
                except Exception as e:
                    print(f"    ❌ 处理失败: {e}")
            else:
                print(f"    ⚠️ 需要安装pandas才能读取Excel文件")
    
    # 保存结果
    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, timestamp)
        os.makedirs(output_path, exist_ok=True)
        
        # 保存为JSON（不依赖pandas）
        result_file = os.path.join(output_path, "results.json")
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 结果保存到: {result_file}")
        
        # 如果有pandas，也保存为Excel
        if PANDAS_AVAILABLE:
            excel_file = os.path.join(output_path, "分析结果.xlsx")
            pd.DataFrame(results).to_excel(excel_file, index=False)
            print(f"✅ Excel结果: {excel_file}")
        
        # 显示结果摘要
        print("\n" + "="*60)
        print("分析结果摘要:")
        print("="*60)
        for r in results:
            print(f"{r['产品']}: 平均{r['平均流量']} L/min, 最大{r['最大流量']} L/min")
        
        return True
    else:
        print("\n⚠️ 没有成功分析任何文件")
        return False

def main_menu():
    """主菜单"""
    while True:
        print("\n" + "="*60)
        print("     氧烛产品分析系统 v1.0")
        print("="*60)
        print("1. 执行数据分析")
        print("2. 创建示例数据")
        print("3. 查看使用说明")
        print("4. 检查环境")
        print("0. 退出程序")
        print("="*60)
        
        choice = input("\n请选择 (0-4): ").strip()
        
        if choice == '0':
            print("\n感谢使用，再见！")
            break
        elif choice == '1':
            simple_analysis()
        elif choice == '2':
            create_test_data()
        elif choice == '3':
            print("\n" + "="*60)
            print("使用说明:")
            print("="*60)
            print("1. 将Excel测试报告放入 reports_input 文件夹")
            print("2. 每个产品创建一个子文件夹")
            print("3. 执行数据分析")
            print("4. 在 reports_output 查看结果")
            print("\n目录结构示例:")
            print("reports_input/")
            print("  ├── 产品A/")
            print("  │   └── 测试数据.xlsx")
            print("  └── 产品B/")
            print("      └── 测试数据.xlsx")
        elif choice == '4':
            print("\n" + "="*60)
            print("环境检查:")
            print("="*60)
            print(f"Python版本: {sys.version}")
            print(f"工作目录: {os.getcwd()}")
            print(f"Pandas可用: {'是' if PANDAS_AVAILABLE else '否'}")
            
            # 检查目录
            for dir_name in ['reports_input', 'reports_output', 'data']:
                exists = os.path.exists(dir_name)
                print(f"{dir_name} 目录: {'✓ 存在' if exists else '✗ 不存在'}")
        else:
            print("⚠️ 无效选择")

def main():
    """主程序入口"""
    try:
        # 设置工作目录
        if getattr(sys, 'frozen', False):
            # 如果是打包的exe
            app_dir = os.path.dirname(sys.executable)
        else:
            # 如果是Python脚本
            app_dir = os.path.dirname(os.path.abspath(__file__))
        
        os.chdir(app_dir)
        
        # 创建必要目录
        for folder in ['reports_input', 'reports_output', 'data']:
            os.makedirs(folder, exist_ok=True)
        
        print("="*60)
        print("     氧烛产品分析系统")
        print("     Windows独立版 v1.0")
        print("="*60)
        print(f"\n工作目录: {os.getcwd()}")
        
        # 运行主菜单
        main_menu()
        
    except Exception as e:
        print(f"\n❌ 程序错误: {e}")
        traceback.print_exc()
    
    print("\n按回车键退出...")
    input()

if __name__ == "__main__":
    main()
