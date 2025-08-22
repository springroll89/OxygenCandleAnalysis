#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的数据提取模块 - 支持文件夹结构
适配每个样品一个文件夹的组织方式
路径: /Users/chunjuan/Documents/OxygenCandleAnalysis/modules/extract_report_data_v2.py
"""

import os
import pandas as pd
import numpy as np
import glob
from datetime import datetime
import json
import re
import shutil
import warnings
warnings.filterwarnings('ignore')

class ImprovedReportExtractor:
    """改进的数据提取器，支持文件夹结构"""
    
    def __init__(self, input_dir="./reports_input", output_dir="./reports_output"):
        """
        初始化
        
        Parameters:
        input_dir: 输入目录，包含各样品文件夹
        output_dir: 输出目录
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.sample_data = []
        self.error_logs = []
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
    def scan_sample_folders(self):
        """扫描所有样品文件夹"""
        print("=" * 60)
        print("扫描样品文件夹")
        print("=" * 60)
        
        # 获取所有子文件夹
        sample_folders = [d for d in os.listdir(self.input_dir) 
                         if os.path.isdir(os.path.join(self.input_dir, d))]
        
        if not sample_folders:
            print(f"❌ 在 {self.input_dir} 下未找到样品文件夹")
            return []
        
        print(f"✅ 找到 {len(sample_folders)} 个样品文件夹")
        
        # 分析每个文件夹
        samples = []
        for folder in sorted(sample_folders):
            folder_path = os.path.join(self.input_dir, folder)
            sample_info = self.analyze_sample_folder(folder, folder_path)
            if sample_info:
                samples.append(sample_info)
                print(f"  ✅ {folder}: {sample_info['status']}")
            else:
                print(f"  ❌ {folder}: 文件不完整")
        
        return samples
    
    def analyze_sample_folder(self, sample_id, folder_path):
        """分析单个样品文件夹"""
        info = {
            'sample_id': sample_id,
            'folder_path': folder_path,
            'csv_file': None,
            'report_file': None,
            'raw_file': None,
            'status': '未知'
        }
        
        # 扫描文件夹内的文件
        files = os.listdir(folder_path)
        
        for file in files:
            file_path = os.path.join(folder_path, file)
            
            # CSV温度文件
            if file.endswith('.csv'):
                info['csv_file'] = file_path
                info['csv_name'] = file
            
            # 分析报告
            elif '分析报告.xlsx' in file:
                info['report_file'] = file_path
                info['report_name'] = file
            
            # 原始数据
            elif file.endswith('.xlsx') and '分析报告' not in file:
                info['raw_file'] = file_path
                info['raw_name'] = file
        
        # 检查文件完整性
        if info['csv_file'] and info['report_file']:
            info['status'] = '完整'
        elif info['report_file']:
            info['status'] = '缺少温度数据'
        elif info['csv_file']:
            info['status'] = '缺少分析报告'
        else:
            return None
        
        return info
    
    def process_all_samples(self):
        """处理所有样品"""
        # 扫描文件夹
        samples = self.scan_sample_folders()
        
        if not samples:
            print("❌ 未找到有效的样品数据")
            return None
        
        print("\n" + "=" * 60)
        print("开始处理样品数据")
        print("=" * 60)
        
        all_data = []
        success_count = 0
        
        for i, sample in enumerate(samples, 1):
            print(f"\n[{i}/{len(samples)}] 处理样品: {sample['sample_id']}")
            
            try:
                # 处理单个样品
                data = self.process_single_sample(sample)
                if data:
                    all_data.append(data)
                    success_count += 1
                    print(f"  ✅ 处理成功")
            except Exception as e:
                error_msg = f"样品 {sample['sample_id']}: {str(e)}"
                self.error_logs.append(error_msg)
                print(f"  ❌ 处理失败: {str(e)}")
        
        print("\n" + "=" * 60)
        print(f"处理完成: 成功 {success_count}/{len(samples)}")
        print("=" * 60)
        
        # 创建汇总DataFrame
        if all_data:
            df = pd.DataFrame(all_data)
            return self.create_summary_report(df)
        
        return None
    
    def process_single_sample(self, sample_info):
        """处理单个样品的所有数据"""
        data = {
            '样品编号': sample_info['sample_id'],
            '文件夹路径': sample_info['folder_path'],
            '处理时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 1. 读取分析报告
        if sample_info['report_file']:
            print(f"  读取报告: {sample_info['report_name']}")
            report_data = self.extract_report_data(sample_info['report_file'])
            data.update(report_data)
        
        # 2. 读取温度数据
        if sample_info['csv_file']:
            print(f"  读取温度: {sample_info['csv_name']}")
            temp_data = self.extract_temperature_data(sample_info['csv_file'])
            data.update(temp_data)
        
        # 3. 关联原始数据（如果需要）
        if sample_info['raw_file']:
            data['原始数据文件'] = sample_info['raw_name']
        
        # 4. 解析样品信息
        self.parse_sample_info(sample_info['sample_id'], data)
        
        return data
    
    def extract_report_data(self, report_file):
        """从分析报告提取数据"""
        data = {}
        
        try:
            xls = pd.ExcelFile(report_file)
            
            # 提取性能指标
            if '性能指标分析' in xls.sheet_names:
                perf_df = pd.read_excel(xls, sheet_name='性能指标分析')
                # 查找平均值行
                avg_row = perf_df[perf_df['设备'].astype(str).str.contains('平均', na=False)]
                if not avg_row.empty:
                    row = avg_row.iloc[0]
                    data['平均启动时长(秒)'] = self.safe_get_value(row, '启动时长(秒)')
                    data['平均达峰时长(秒)'] = self.safe_get_value(row, '达峰时长(秒)')
                    data['平均累计流量(升)'] = self.safe_get_value(row, '累计流量(升)')
                    data['平均达标率(%)'] = self.safe_get_value(row, '达标率(%)')
                    data['平均产氧时间(分钟)'] = self.safe_get_value(row, '产氧时间(分钟)')
            
            # 提取点火测试数据
            if '点火测试记录数据' in xls.sheet_names:
                ignition_df = pd.read_excel(xls, sheet_name='点火测试记录数据')
                total_row = ignition_df[ignition_df['传感器'].astype(str).str.contains('总计', na=False)]
                if not total_row.empty:
                    row = total_row.iloc[0]
                    data['反应总时长(秒)'] = self.safe_get_value(row, '反应总时长(秒)')
                    data['总累积供氧(升)'] = self.safe_get_value(row, '总累积供氧(升)')
                    
                    # 温度数据（从报告中）
                    data['外壳最高温度(°C)'] = self.safe_get_value(row, '外壳最高温度(°C)')
                    data['隔热垫外最高温度(°C)'] = self.safe_get_value(row, '隔热垫外最高温度(°C)')
                    data['供氧口最高温度(°C)'] = self.safe_get_value(row, '供氧口最高温度(°C)')
            
            # 提取平稳性分析
            if '平稳性分析' in xls.sheet_names:
                stability_df = pd.read_excel(xls, sheet_name='平稳性分析', header=None)
                for idx, row in stability_df.iterrows():
                    if pd.notna(row[0]):
                        label = str(row[0])
                        value = row[1] if pd.notna(row[1]) else None
                        if '相对基准线变异系数' in label and value is not None:
                            data['CV值'] = float(value)
                        elif '拟合斜率' in label and value is not None:
                            data['拟合斜率'] = float(value)
            
        except Exception as e:
            print(f"    ⚠️ 提取报告数据出错: {str(e)}")
        
        return data
    
    def extract_temperature_data(self, csv_file):
        """从CSV文件提取温度数据"""
        data = {}
        
        try:
            # 尝试不同的编码
            for encoding in ['gbk', 'gb2312', 'utf-8', 'latin1']:
                try:
                    temp_df = pd.read_csv(csv_file, encoding=encoding)
                    break
                except:
                    continue
            
            # 检查是否有CH1-CH6列
            temp_cols = ['CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6']
            if all(col in temp_df.columns for col in temp_cols):
                # 计算各通道最高温度
                # CH1-CH3: 外壳
                shell_temps = temp_df[['CH1', 'CH2', 'CH3']].max().max()
                # CH4-CH5: 隔热垫
                insulation_temps = temp_df[['CH4', 'CH5']].max().max()
                # CH6: 供氧口
                outlet_temp = temp_df['CH6'].max()
                
                data['CSV外壳最高温度(°C)'] = round(shell_temps, 1)
                data['CSV隔热垫最高温度(°C)'] = round(insulation_temps, 1)
                data['CSV供氧口最高温度(°C)'] = round(outlet_temp, 1)
                data['温度数据点数'] = len(temp_df)
                
        except Exception as e:
            print(f"    ⚠️ 读取温度数据出错: {str(e)}")
        
        return data
    
    def parse_sample_info(self, sample_id, data):
        """解析样品编号信息"""
        # 解析样品编号中的信息
        # 例如: 2A143, 2A145LT, 2A146MT, 2A147(HT)
        
        data['样品系列'] = '2A' if '2A' in sample_id else '未知'
        
        # 提取数字编号
        numbers = re.findall(r'\d+', sample_id)
        if numbers:
            data['样品序号'] = numbers[-1]
        
        # 提取后缀（LT, MT, HT等）
        if 'LT' in sample_id:
            data['温度等级'] = '低温(LT)'
        elif 'MT' in sample_id:
            data['温度等级'] = '中温(MT)'
        elif 'HT' in sample_id:
            data['温度等级'] = '高温(HT)'
        else:
            data['温度等级'] = '标准'
        
        # 根据编号推测配方（这里需要根据实际情况调整）
        if '143' in sample_id:
            data['配方代号'] = 'A1'
        elif '144' in sample_id:
            data['配方代号'] = 'A2'
        elif '145' in sample_id:
            data['配方代号'] = 'B1'
        elif '146' in sample_id:
            data['配方代号'] = 'B2'
        elif '147' in sample_id:
            data['配方代号'] = 'C1'
        else:
            data['配方代号'] = '未知'
    
    def safe_get_value(self, row, column, default=np.nan):
        """安全获取数值"""
        try:
            if column in row.index:
                val = row[column]
                if pd.notna(val) and val != '' and val != '-':
                    return float(val)
        except:
            pass
        return default
    
    def create_summary_report(self, df):
        """创建汇总报告"""
        # 重新排列列
        priority_cols = [
            '样品编号', '样品系列', '样品序号', '温度等级', '配方代号',
            '平均达标率(%)', 'CV值', '反应总时长(秒)', '总累积供氧(升)',
            '外壳最高温度(°C)', '隔热垫外最高温度(°C)', '供氧口最高温度(°C)',
            'CSV外壳最高温度(°C)', 'CSV隔热垫最高温度(°C)', 'CSV供氧口最高温度(°C)'
        ]
        
        # 保留存在的列
        available_cols = [col for col in priority_cols if col in df.columns]
        other_cols = [col for col in df.columns if col not in available_cols]
        
        final_df = df[available_cols + other_cols]
        
        # 保存到Excel
        output_file = os.path.join(self.output_dir, '样品数据汇总.xlsx')
        
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            # 主数据表
            final_df.to_excel(writer, sheet_name='数据汇总', index=False)
            
            # 添加统计表
            self.create_statistics_sheet(final_df, writer)
            
            # 添加错误日志
            if self.error_logs:
                error_df = pd.DataFrame({'错误信息': self.error_logs})
                error_df.to_excel(writer, sheet_name='错误日志', index=False)
            
            # 格式化
            workbook = writer.book
            worksheet = writer.sheets['数据汇总']
            
            # 设置列宽
            for idx, col in enumerate(final_df.columns):
                max_len = max(
                    final_df[col].astype(str).str.len().max(),
                    len(col)
                ) + 2
                worksheet.set_column(idx, idx, min(max_len, 30))
        
        print(f"\n✅ 汇总报告已保存: {output_file}")
        print(f"   处理样品数: {len(final_df)}")
        print(f"   数据指标数: {len(final_df.columns)}")
        
        return final_df
    
    def create_statistics_sheet(self, df, writer):
        """创建统计摘要"""
        stats_data = []
        
        # 数值列统计
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if df[col].notna().sum() > 0:
                stats_data.append({
                    '指标': col,
                    '有效数据': df[col].notna().sum(),
                    '平均值': round(df[col].mean(), 3),
                    '标准差': round(df[col].std(), 3),
                    '最小值': round(df[col].min(), 3),
                    '最大值': round(df[col].max(), 3)
                })
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            stats_df.to_excel(writer, sheet_name='统计摘要', index=False)
    
    def copy_samples_to_output(self):
        """复制处理后的文件到输出目录（可选）"""
        print("\n复制文件到输出目录...")
        
        samples = self.scan_sample_folders()
        
        for sample in samples:
            if sample['report_file']:
                # 创建输出文件夹
                output_folder = os.path.join(self.output_dir, sample['sample_id'])
                os.makedirs(output_folder, exist_ok=True)
                
                # 复制分析报告（重命名）
                new_report_name = f"{sample['sample_id']}_分析报告.xlsx"
                output_report = os.path.join(output_folder, new_report_name)
                shutil.copy2(sample['report_file'], output_report)
                
                print(f"  ✅ 复制: {sample['sample_id']}")


# 使用示例
if __name__ == "__main__":
    print("=" * 60)
    print("氧烛产品数据提取系统 v2.0")
    print("支持文件夹结构")
    print("=" * 60)
    
    # 设置路径
    input_dir = "/Users/chunjuan/Documents/OxygenCandleAnalysis/reports_input"
    output_dir = "/Users/chunjuan/Documents/OxygenCandleAnalysis/reports_output"
    
    # 创建提取器
    extractor = ImprovedReportExtractor(input_dir, output_dir)
    
    # 处理所有样品
    df = extractor.process_all_samples()
    
    if df is not None:
        print("\n" + "=" * 60)
        print("数据提取完成 - 统计摘要")
        print("=" * 60)
        print(f"样品总数: {len(df)}")
        
        # 按温度等级统计
        if '温度等级' in df.columns:
            print("\n温度等级分布:")
            print(df['温度等级'].value_counts())
        
        # 按配方统计
        if '配方代号' in df.columns:
            print("\n配方分布:")
            print(df['配方代号'].value_counts())
        
        # 关键指标范围
        if '平均达标率(%)' in df.columns:
            print(f"\n达标率范围: {df['平均达标率(%)'].min():.1f}% - {df['平均达标率(%)'].max():.1f}%")
    else:
        print("\n❌ 数据提取失败")