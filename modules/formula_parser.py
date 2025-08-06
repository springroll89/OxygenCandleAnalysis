#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配方解析和对比模块 - 支持温度标记
"""

import pandas as pd
import re
import os

class FormulaParser:
    """配方解析器"""
    
    def __init__(self, formula_file="./data/配方表.xlsx"):
        """初始化配方解析器"""
        self.formula_file = formula_file
        self.formulas_data = {}
        self.main_table = None
        self.product_formulas = {}
        self.load_formulas()
    
    def load_formulas(self):
        """加载配方数据"""
        # 尝试多个可能的文件位置
        possible_files = [
            "./data/配方表.xlsx",
            "./配方表.xlsx",
            "配方表.xlsx",
            self.formula_file
        ]
        
        file_found = None
        for file_path in possible_files:
            if os.path.exists(file_path):
                file_found = file_path
                print(f"✅ 找到配方文件: {file_found}")
                break
        
        if not file_found:
            print(f"⚠️ 未找到配方文件")
            return
        
        try:
            # 读取Excel文件
            xls = pd.ExcelFile(file_found)
            print(f"Sheet列表: {xls.sheet_names}")
            
            # 读取总表
            main_sheet = None
            for sheet in xls.sheet_names:
                if '总表' in sheet.lower():
                    main_sheet = sheet
                    break
            
            if main_sheet:
                self.main_table = pd.read_excel(file_found, sheet_name=main_sheet)
                print(f"✅ 加载总表: {len(self.main_table)} 条记录")
                
                # 解析每个产品的配方
                for idx, row in self.main_table.iterrows():
                    # 获取产品ID和配方
                    product_id = None
                    formula_str = None
                    
                    # 产品序号
                    if '产品序号' in self.main_table.columns:
                        product_id = str(row['产品序号'])
                    elif '序号' in self.main_table.columns:
                        product_id = str(row['序号'])
                    else:
                        product_id = str(row.iloc[0])
                    
                    # 配方/物料
                    if '物料' in self.main_table.columns:
                        formula_str = str(row['物料'])
                    elif '配方' in self.main_table.columns:
                        formula_str = str(row['配方'])
                    else:
                        formula_str = str(row.iloc[1])
                    
                    if product_id and formula_str and product_id != 'nan' and formula_str != 'nan':
                        parsed = self.parse_formula_string(formula_str)
                        if parsed:
                            self.product_formulas[product_id] = {
                                'formula_string': formula_str,
                                'layers': parsed
                            }
                
                print(f"✅ 解析了 {len(self.product_formulas)} 个产品配方")
            
            # 读取各层配方（支持大小写）
            for sheet_name in xls.sheet_names:
                sheet_lower = sheet_name.lower()
                if 'a层' in sheet_lower or sheet_lower == 'a层':
                    df = pd.read_excel(file_found, sheet_name=sheet_name)
                    self.formulas_data['A层'] = df
                    print(f"✅ 加载A层: {len(df)} 个配方")
                elif 'b层' in sheet_lower or sheet_lower == 'b层':
                    df = pd.read_excel(file_found, sheet_name=sheet_name)
                    self.formulas_data['B层'] = df
                    print(f"✅ 加载B层: {len(df)} 个配方")
                elif 'c层' in sheet_lower or sheet_lower == 'c层':
                    df = pd.read_excel(file_found, sheet_name=sheet_name)
                    self.formulas_data['C层'] = df
                    print(f"✅ 加载C层: {len(df)} 个配方")
            
        except Exception as e:
            print(f"❌ 加载配方失败: {e}")
            import traceback
            traceback.print_exc()
    
    def clean_product_id(self, product_id):
        """
        清理产品ID，去除温度标记
        例如：2A143(MT) -> 2A143
        """
        if not product_id:
            return product_id
        
        # 去除括号及其内容 (MT), (LT), (HT), (STD) 等
        cleaned = re.sub(r'\([^)]*\)', '', str(product_id)).strip()
        return cleaned
    
    def parse_formula_string(self, formula_str):
        """解析配方字符串"""
        if pd.isna(formula_str) or not formula_str or formula_str == 'nan':
            return {}
        
        formula_dict = {}
        
        # 统一括号格式
        formula_str = str(formula_str).replace('（', '(').replace('）', ')')
        
        # 使用正则表达式解析
        pattern = r'([A-Z]\d+)\((\d+)g\)?'
        matches = re.findall(pattern, formula_str)
        
        c_layer_count = 0
        
        for code, weight in matches:
            if code.startswith('A'):
                layer = 'A层'
            elif code.startswith('B'):
                layer = 'B层'
            elif code.startswith('C'):
                c_layer_count += 1
                layer = f'C{c_layer_count}层'
            else:
                layer = '未知层'
            
            formula_dict[layer] = {
                'code': code,
                'weight': int(weight)
            }
        
        return formula_dict
    
    def get_formula_details(self, formula_code, layer_name):
        """获取配方的详细成分"""
        base_layer = layer_name.replace('1', '').replace('2', '').replace('3', '')
        
        if base_layer not in self.formulas_data:
            return {}
        
        layer_df = self.formulas_data[base_layer]
        
        if len(layer_df) > 0:
            # 在第一列查找配方代码
            formula_row = layer_df[layer_df.iloc[:, 0] == formula_code]
            
            if formula_row.empty:
                return {}
            
            details = {}
            row = formula_row.iloc[0]
            
            # 从第二列开始是成分
            for i, col in enumerate(layer_df.columns[1:], 1):
                value = row.iloc[i]
                if pd.notna(value) and value != 0 and value != '':
                    # 处理百分比
                    if isinstance(value, str) and '%' in value:
                        value = float(value.replace('%', ''))
                    details[col] = float(value)
            
            return details
        
        return {}
    
    def get_product_formula(self, product_id):
        """
        获取产品的完整配方
        支持带温度标记的产品ID
        """
        # 先尝试原始ID
        if product_id in self.product_formulas:
            formula_data = self.product_formulas[product_id]
        else:
            # 尝试清理后的ID
            cleaned_id = self.clean_product_id(product_id)
            if cleaned_id in self.product_formulas:
                formula_data = self.product_formulas[cleaned_id]
            else:
                return None
        
        complete_formula = {
            'product_id': product_id,  # 保留原始ID用于显示
            'formula_string': formula_data['formula_string'],
            'layers': {}
        }
        
        for layer, info in formula_data['layers'].items():
            code = info['code']
            weight = info['weight']
            details = self.get_formula_details(code, layer)
            
            complete_formula['layers'][layer] = {
                'code': code,
                'weight': weight,
                'components': details
            }
        
        return complete_formula
    
    def calculate_component_changes(self, base_info, target_info, layer):
        """计算成分的具体变化（考虑重量）"""
        changes = []
        
        base_code = base_info['code']
        target_code = target_info['code']
        base_weight = base_info['weight']
        target_weight = target_info['weight']
        
        # 获取成分详情
        base_comp = self.get_formula_details(base_code, layer)
        target_comp = self.get_formula_details(target_code, layer)
        
        if base_code == target_code:
            # 配方相同，只是重量变化
            if base_weight != target_weight and base_comp:
                for comp_name, comp_percent in base_comp.items():
                    base_amount = base_weight * comp_percent / 100
                    target_amount = target_weight * comp_percent / 100
                    change = target_amount - base_amount
                    
                    if abs(change) > 0.01:  # 忽略很小的变化
                        changes.append({
                            'component': comp_name,
                            'type': '重量变化',
                            'base_percent': comp_percent,
                            'target_percent': comp_percent,
                            'base_amount': round(base_amount, 2),
                            'target_amount': round(target_amount, 2),
                            'change': round(change, 2),
                            'description': f"{comp_name}: {base_amount:.2f}g → {target_amount:.2f}g ({change:+.2f}g)"
                        })
        else:
            # 配方不同，对比成分
            all_components = set(base_comp.keys()) | set(target_comp.keys())
            
            for comp_name in all_components:
                base_percent = base_comp.get(comp_name, 0)
                target_percent = target_comp.get(comp_name, 0)
                
                base_amount = base_weight * base_percent / 100
                target_amount = target_weight * target_percent / 100
                change = target_amount - base_amount
                
                if base_percent == 0 and target_percent > 0:
                    # 新增成分
                    changes.append({
                        'component': comp_name,
                        'type': '新增',
                        'base_percent': 0,
                        'target_percent': target_percent,
                        'base_amount': 0,
                        'target_amount': round(target_amount, 2),
                        'change': round(target_amount, 2),
                        'description': f"新增 {comp_name}: {target_amount:.2f}g ({target_percent}%)"
                    })
                elif base_percent > 0 and target_percent == 0:
                    # 删除成分
                    changes.append({
                        'component': comp_name,
                        'type': '删除',
                        'base_percent': base_percent,
                        'target_percent': 0,
                        'base_amount': round(base_amount, 2),
                        'target_amount': 0,
                        'change': round(-base_amount, 2),
                        'description': f"删除 {comp_name}: -{base_amount:.2f}g"
                    })
                elif abs(change) > 0.01:
                    # 成分变化
                    changes.append({
                        'component': comp_name,
                        'type': '变化',
                        'base_percent': base_percent,
                        'target_percent': target_percent,
                        'base_amount': round(base_amount, 2),
                        'target_amount': round(target_amount, 2),
                        'change': round(change, 2),
                        'description': f"{comp_name}: {base_amount:.2f}g({base_percent}%) → {target_amount:.2f}g({target_percent}%) ({change:+.2f}g)"
                    })
        
        return changes
    
    def compare_two_formulas(self, base_formula, target_formula):
        """对比两个配方的差异（增强版）"""
        diff = {
            'formula_string': target_formula['formula_string'],
            'differences': [],
            'component_details': {}  # 成分详细变化
        }
        
        base_layers = base_formula['layers']
        target_layers = target_formula['layers']
        
        # 获取所有层
        all_layers = set(base_layers.keys()) | set(target_layers.keys())
        
        for layer in sorted(all_layers):
            if layer in base_layers and layer not in target_layers:
                # 基准有，目标没有
                base_info = base_layers[layer]
                diff['differences'].append({
                    'type': '缺少',
                    'layer': layer,
                    'code': base_info['code'],
                    'weight': f"-{base_info['weight']}g",
                    'description': f"缺少 {layer}: {base_info['code']} ({base_info['weight']}g)"
                })
                
                # 计算删除的成分
                base_comp = self.get_formula_details(base_info['code'], layer)
                component_changes = []
                for comp_name, comp_percent in base_comp.items():
                    amount = base_info['weight'] * comp_percent / 100
                    component_changes.append({
                        'component': comp_name,
                        'type': '删除',
                        'base_amount': round(amount, 2),
                        'target_amount': 0,
                        'change': round(-amount, 2),
                        'description': f"删除 {comp_name}: -{amount:.2f}g"
                    })
                
                if component_changes:
                    diff['component_details'][layer] = component_changes
                    
            elif layer not in base_layers and layer in target_layers:
                # 基准没有，目标有
                target_info = target_layers[layer]
                diff['differences'].append({
                    'type': '新增',
                    'layer': layer,
                    'code': target_info['code'],
                    'weight': f"+{target_info['weight']}g",
                    'description': f"新增 {layer}: {target_info['code']} ({target_info['weight']}g)"
                })
                
                # 计算新增的成分
                target_comp = self.get_formula_details(target_info['code'], layer)
                component_changes = []
                for comp_name, comp_percent in target_comp.items():
                    amount = target_info['weight'] * comp_percent / 100
                    component_changes.append({
                        'component': comp_name,
                        'type': '新增',
                        'base_amount': 0,
                        'target_amount': round(amount, 2),
                        'change': round(amount, 2),
                        'description': f"新增 {comp_name}: {amount:.2f}g ({comp_percent}%)"
                    })
                
                if component_changes:
                    diff['component_details'][layer] = component_changes
                    
            elif layer in base_layers and layer in target_layers:
                base_info = base_layers[layer]
                target_info = target_layers[layer]
                
                # 比较配方代码
                if base_info['code'] != target_info['code']:
                    diff['differences'].append({
                        'type': '配方变化',
                        'layer': layer,
                        'code': f"{base_info['code']} → {target_info['code']}",
                        'description': f"{layer} 配方变化: {base_info['code']} → {target_info['code']}"
                    })
                
                # 比较重量
                if base_info['weight'] != target_info['weight']:
                    weight_diff = target_info['weight'] - base_info['weight']
                    sign = "+" if weight_diff > 0 else ""
                    diff['differences'].append({
                        'type': '重量变化',
                        'layer': layer,
                        'code': base_info['code'],
                        'weight': f"{base_info['weight']}g → {target_info['weight']}g ({sign}{weight_diff}g)",
                        'description': f"{layer} 重量变化: {base_info['weight']}g → {target_info['weight']}g ({sign}{weight_diff}g)"
                    })
                
                # 计算成分的具体变化
                component_changes = self.calculate_component_changes(base_info, target_info, layer)
                if component_changes:
                    diff['component_details'][layer] = component_changes
        
        return diff
    
    def compare_formulas(self, product_ids):
        """
        对比多个产品的配方差异
        支持带温度标记的产品ID
        """
        if not product_ids or len(product_ids) < 2:
            return {"message": "需要至少2个产品进行对比"}
        
        # 获取所有产品的配方（支持带温度标记的ID）
        formulas = {}
        not_found = []
        
        for pid in product_ids:
            formula = self.get_product_formula(pid)
            if formula:
                formulas[pid] = formula
            else:
                # 尝试清理后的ID
                cleaned_id = self.clean_product_id(pid)
                not_found.append(f"{pid} (尝试了 {cleaned_id})")
        
        if len(formulas) < 2:
            available = list(self.product_formulas.keys())[:10]
            return {
                "message": f"未找到足够的配方数据。\n未找到: {', '.join(not_found)}\n可用的产品ID示例: {', '.join(available)}"
            }
        
        # 以第一个产品为基准
        base_id = None
        base_formula = None
        
        # 找到第一个有效的配方作为基准
        for pid in product_ids:
            if pid in formulas:
                base_id = pid
                base_formula = formulas[pid]
                break
        
        if not base_formula:
            return {"message": "未找到有效的基准配方"}
        
        # 对比结果
        comparison = {
            'base_product': base_id,
            'base_formula': base_formula['formula_string'],
            'comparisons': {}
        }
        
        # 对比其他产品
        for pid in product_ids:
            if pid == base_id:
                continue
                
            if pid not in formulas:
                cleaned_id = self.clean_product_id(pid)
                comparison['comparisons'][pid] = {
                    'status': f'未找到配方 (尝试了 {cleaned_id})'
                }
                continue
            
            target_formula = formulas[pid]
            diff = self.compare_two_formulas(base_formula, target_formula)
            comparison['comparisons'][pid] = diff
        
        return comparison
    
    def format_comparison_for_display(self, comparison):
        """格式化对比结果用于显示"""
        if not comparison or 'comparisons' not in comparison:
            return []
        
        display_data = []
        
        for product_id, diff in comparison['comparisons'].items():
            if 'status' in diff:
                display_data.append({
                    '产品': product_id,
                    '配方': '未找到',
                    '差异描述': diff['status']
                })
                continue
                
            if 'differences' not in diff:
                continue
            
            # 汇总差异
            summary = {
                '产品': product_id,
                '配方': diff.get('formula_string', ''),
                '差异汇总': [],
                '成分变化': []
            }
            
            # 添加配方差异
            for d in diff['differences']:
                summary['差异汇总'].append(d['description'])
            
            # 添加成分变化
            if 'component_details' in diff:
                for layer, changes in diff['component_details'].items():
                    for change in changes:
                        summary['成分变化'].append(f"{layer} - {change['description']}")
            
            if summary['差异汇总']:
                summary['差异描述'] = '\n'.join(summary['差异汇总'])
            else:
                summary['差异描述'] = '配方相同'
            
            if summary['成分变化']:
                summary['成分变化描述'] = '\n'.join(summary['成分变化'])
            else:
                summary['成分变化描述'] = '无成分变化'
            
            display_data.append(summary)
        
        return display_data


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("测试配方解析器 - 支持温度标记")
    print("=" * 60)
    
    # 创建解析器
    parser = FormulaParser()
    
    # 打印加载的产品数量
    print(f"\n已加载 {len(parser.product_formulas)} 个产品配方")
    
    # 测试清理ID功能
    test_ids = ["2A143(MT)", "2A144(LT)", "2A145", "2A146(HT)"]
    print("\n测试ID清理:")
    for test_id in test_ids:
        cleaned = parser.clean_product_id(test_id)
        print(f"  {test_id} -> {cleaned}")
    
    # 测试带温度标记的对比
    if parser.product_formulas:
        print("\n测试带温度标记的配方对比:")
        test_compare = ["2A143(MT)", "2A144(LT)"]
        comparison = parser.compare_formulas(test_compare)
        
        if 'message' in comparison:
            print(f"⚠️ {comparison['message']}")
        else:
            print(f"✅ 对比成功")
            print(f"基准产品: {comparison.get('base_product')}")
            for pid, diff in comparison.get('comparisons', {}).items():
                if 'status' in diff:
                    print(f"  {pid}: {diff['status']}")
                elif 'differences' in diff:
                    print(f"  {pid}: {len(diff['differences'])} 个差异")
