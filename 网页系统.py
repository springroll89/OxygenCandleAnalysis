#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
氧烛分析Web系统 - 完整版v1.4
包含配方差异分析、单产品配方组支持和高级分析模块
修复了配方优化显示和故障诊断建议
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import glob
import numpy as np
import sys
sys.path.append('./modules')
from datetime import datetime

# 尝试导入配方解析模块
try:
    from modules.formula_parser import FormulaParser
    FORMULA_MODULE_LOADED = True
except:
    FORMULA_MODULE_LOADED = False

# ⚠️ 页面配置必须是第一个Streamlit命令
st.set_page_config(
    page_title="氧烛分析系统",
    page_icon="🔥",
    layout="wide"
)
# ===== 初始化session_state =====
if 'zoom_level' not in st.session_state:
    st.session_state.zoom_level = 100
if 'display_mode' not in st.session_state:
    st.session_state.display_mode = "标准视图"
if 'show_time_range' not in st.session_state:
    st.session_state.show_time_range = False
if 'target_score_ml' not in st.session_state:
    st.session_state.target_score_ml = 90
# 添加以下新的状态
if 'kinetics_results' not in st.session_state:
    st.session_state.kinetics_results = None
if 'kinetics_sample' not in st.session_state:
    st.session_state.kinetics_sample = None
if 'ml_optimization_result' not in st.session_state:
    st.session_state.ml_optimization_result = None
if 'ml_target_score_used' not in st.session_state:
    st.session_state.ml_target_score_used = None

# ===== 密码验证部分 =====
PASSWORD = os.environ.get("OXYGEN_CANDLE_PASSWORD", "").strip()
if not PASSWORD:
    st.error("未配置 OXYGEN_CANDLE_PASSWORD，应用已停止。")
    st.stop()

def check_password():
    """简单密码验证"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        # 创建一个居中的登录框
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.title("🔐 AWK产品分析系统")
            st.markdown("---")
            
            with st.form("login_form"):
                password = st.text_input("请输入密码：", type="password")
                submit_button = st.form_submit_button("登录", use_container_width=True)
                
                if submit_button:
                    if password == PASSWORD:
                        st.session_state.logged_in = True
                        st.success("✅ 登录成功！")
                        st.rerun()
                    else:
                        st.error("❌ 密码错误！")
            
            st.markdown("---")
            st.caption("💡 提示：如忘记密码请联系管理员")
        
        return False
    return True

# 主程序入口 - 密码验证
if not check_password():
    st.stop()

# ===== 以下是主程序代码 =====

# 标题
st.title("🔥 氧烛产品分析系统")
st.markdown("---")

# 侧边栏
st.sidebar.header("📊 功能导航")
page = st.sidebar.radio(
    "选择功能",
    ["主页", "数据总览", "排名分析", "对比分析", "配方组对比", "最佳配方", "高级分析"]
)

# 添加退出登录按钮
if st.sidebar.button("🚪 退出登录"):
    st.session_state.logged_in = False
    st.rerun()

# 读取数据
@st.cache_data
def load_data():
    """加载数据 - 智能查找最新的数据文件"""
    
    # 方案1：先尝试读取current_session.txt找到最新文件夹
    try:
        with open('./reports_output/current_session.txt', 'r') as f:
            timestamp = f.read().strip()
        ranking_file = f"./reports_output/{timestamp}/样品评分排名.xlsx"
        if os.path.exists(ranking_file):
            ranking_df = pd.read_excel(ranking_file, sheet_name='排名表')
            stats_df = pd.read_excel(ranking_file, sheet_name='分组统计')
            st.sidebar.success(f"数据来源: {timestamp}")
            return ranking_df, stats_df, timestamp
    except:
        pass
    
    # 方案2：直接在reports_output根目录查找
    ranking_file = "./reports_output/样品评分排名.xlsx"
    if os.path.exists(ranking_file):
        ranking_df = pd.read_excel(ranking_file, sheet_name='排名表')
        stats_df = pd.read_excel(ranking_file, sheet_name='分组统计')
        st.sidebar.success("数据来源: reports_output/")
        return ranking_df, stats_df, None
    
    # 方案3：查找所有时间戳文件夹，使用最新的
    folders = glob.glob("./reports_output/*/")
    if folders:
        folders.sort()
        latest_folder = folders[-1]
        ranking_file = os.path.join(latest_folder, "样品评分排名.xlsx")
        if os.path.exists(ranking_file):
            ranking_df = pd.read_excel(ranking_file, sheet_name='排名表')
            stats_df = pd.read_excel(ranking_file, sheet_name='分组统计')
            folder_name = os.path.basename(os.path.normpath(latest_folder))
            st.sidebar.success(f"数据来源: {folder_name}")
            return ranking_df, stats_df, folder_name
    
    return None, None, None

# 加载基准曲线
@st.cache_data
def load_baseline():
    """加载基准曲线数据"""
    baseline_file = "./data/基准曲线.csv"
    if os.path.exists(baseline_file):
        try:
            baseline_df = pd.read_csv(baseline_file)
            return baseline_df
        except:
            pass
    return None

# 加载流量数据的函数
@st.cache_data
def load_flow_data(sample_id):
    """加载样品的流量数据和燃烧深度数据"""
    input_folder = f"./reports_input/{sample_id}"
    
    # 查找分析报告文件
    report_files = glob.glob(os.path.join(input_folder, "*_分析报告.xlsx"))
    if report_files:
        try:
            xls = pd.ExcelFile(report_files[0])
            
            # 读取原始数据
            flow_data = None
            if '原始数据' in xls.sheet_names:
                flow_data = pd.read_excel(report_files[0], sheet_name='原始数据')
            
            # 读取燃烧深度数据
            depth_data = None
            if '产氧-深度曲线' in xls.sheet_names:
                depth_data = pd.read_excel(report_files[0], sheet_name='产氧-深度曲线')
            
            return flow_data, depth_data
        except Exception as e:
            st.warning(f"读取{sample_id}数据时出错: {e}")
    return None, None

# 获取配方解析器
def get_formula_parser():
    """获取配方解析器实例"""
    if FORMULA_MODULE_LOADED:
        try:
            parser = FormulaParser("./data/配方表.xlsx")
            if parser and parser.product_formulas:
                return parser
        except Exception as e:
            st.error(f"配方解析器初始化失败: {e}")
    return None

# 提取产品配方信息
def extract_formula_from_id(product_id, parser):
    """从产品ID提取配方信息"""
    if not parser:
        return None
    
    # 清理产品ID（去除温度标记）
    cleaned_id = parser.clean_product_id(product_id)
    
    # 获取配方
    if cleaned_id in parser.product_formulas:
        return parser.product_formulas[cleaned_id]['formula_string']
    
    return None

# 按配方分组产品
def group_products_by_formula(ranking_df, parser, include_single=False):
    """
    按配方对产品进行分组
    
    Parameters:
    - ranking_df: 排名数据
    - parser: 配方解析器
    - include_single: 是否包含只有一个产品的配方组
    """
    formula_groups = {}
    
    if not parser:
        return formula_groups
    
    for idx, row in ranking_df.iterrows():
        product_id = row['样品编号']
        formula = extract_formula_from_id(product_id, parser)
        
        if formula:
            if formula not in formula_groups:
                formula_groups[formula] = []
            formula_groups[formula].append(product_id)
    
    # 根据参数决定是否过滤单个产品的配方组
    if not include_single:
        formula_groups = {k: v for k, v in formula_groups.items() if len(v) > 1}
    
    return formula_groups

# 对比分析组件（完整版，包含配方差异）
def show_comparison_component(selected_products, ranking_df, title_prefix=""):
    """显示对比分析组件（可复用）"""
    
    if not selected_products:
        st.warning("请选择要对比的产品")
        return
    
    # 筛选数据
    compare_df = ranking_df[ranking_df['样品编号'].isin(selected_products)]
    
    # 创建五个标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 流量曲线对比", 
        "📊 燃烧深度分析", 
        "🧪 配方差异",
        "🔬 性能指标对比", 
        "📋 详细数据"
    ])
    
    with tab1:
        st.subheader(f"{title_prefix}流量曲线对比")
        
        # 创建流量曲线图
        fig = go.Figure()
        
        # 用于记录所有数据的最大值
        max_flow = 0
        
        # 加载并添加基准曲线
        baseline_df = load_baseline()
        if baseline_df is not None:
            fig.add_trace(go.Scatter(
                x=baseline_df['time'],
                y=baseline_df['flow'],
                mode='lines',
                name='基准曲线',
                line=dict(color='red', width=2.5, dash='dash'),
                hovertemplate='时间: %{x:.1f}秒<br>流量: %{y:.2f} L/min'
            ))
            max_flow = max(max_flow, baseline_df['flow'].max())
        
        # 颜色列表
        colors_list = ['blue', 'green', 'orange', 'purple', 'brown', 'pink', 'cyan', 'magenta']
        
        # 为每个选中的样品添加流量曲线
        for idx, sample_id in enumerate(selected_products):
            flow_data, _ = load_flow_data(sample_id)
            
            if flow_data is not None and '时间(s)' in flow_data.columns and '平均流量L/Min' in flow_data.columns:
                fig.add_trace(go.Scatter(
                    x=flow_data['时间(s)'],
                    y=flow_data['平均流量L/Min'],
                    mode='lines',
                    name=sample_id,
                    line=dict(color=colors_list[idx % len(colors_list)], width=2),
                    hovertemplate='%{fullData.name}<br>时间: %{x:.1f}秒<br>流量: %{y:.2f} L/min'
                ))
                max_flow = max(max_flow, flow_data['平均流量L/Min'].max())
        
        # 计算Y轴范围
        y_max = max_flow * 1.1 if max_flow > 0 else 10
        
        # 更新布局
        fig.update_layout(
            title=f"{title_prefix}流量曲线对比图",
            xaxis=dict(
                title="时间 (秒)",
                rangeslider=dict(
                    visible=True,
                    thickness=0.05
                ),
                type="linear"
            ),
            yaxis=dict(
                title="流量 (L/Min)",
                range=[0, y_max]
            ),
            hovermode='x unified',
            height=600,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 使用说明
        with st.expander("💡 使用说明"):
            st.info("""
            - 拖动底部滑块可以放大查看特定时间段
            - 鼠标悬停查看具体数值
            - 点击图例可以显示/隐藏对应曲线
            - 双击图例可以单独显示某条曲线
            """)
    
    with tab2:
        st.subheader(f"{title_prefix}燃烧深度分析")
        
        # 创建燃烧深度对比图
        fig2 = make_subplots(
            rows=2, cols=1,
            row_heights=[0.7, 0.3],
            subplot_titles=("燃烧深度随时间变化", "燃烧速率对比"),
            vertical_spacing=0.15
        )
        
        # 存储每个样品的燃烧数据
        burn_data = {}
        colors_list = ['blue', 'green', 'orange', 'purple', 'brown', 'pink', 'cyan', 'magenta']
        
        for idx, sample_id in enumerate(selected_products):
            _, depth_data = load_flow_data(sample_id)
            
            if depth_data is not None:
                # 查找时间和深度列
                time_col = None
                depth_col = None
                
                for col in depth_data.columns:
                    if '时间' in col or 'time' in col.lower():
                        time_col = col
                    if '深度' in col or '刻度' in col or 'depth' in col.lower():
                        depth_col = col
                
                if time_col and depth_col:
                    # 清洗数据
                    valid_data = depth_data[[time_col, depth_col]].dropna()
                    
                    if not valid_data.empty:
                        # 添加燃烧深度曲线
                        fig2.add_trace(
                            go.Scatter(
                                x=valid_data[time_col],
                                y=valid_data[depth_col],
                                mode='lines+markers',
                                name=sample_id,
                                line=dict(color=colors_list[idx % len(colors_list)], width=2),
                                marker=dict(size=4)
                            ),
                            row=1, col=1
                        )
                        
                        burn_data[sample_id] = valid_data
        
        # 更新布局
        fig2.update_xaxes(title_text="时间 (秒)", row=2, col=1)
        fig2.update_yaxes(title_text="燃烧深度 (mm)", row=1, col=1)
        
        fig2.update_layout(
            height=600,
            showlegend=True,
            hovermode='x unified'
        )
        
        if burn_data:
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.warning("未找到燃烧深度数据")
    
    with tab3:
        st.subheader(f"{title_prefix}配方差异分析")
        
        # 获取配方解析器
        parser = get_formula_parser()
        
        if not parser:
            st.warning("配方解析模块未加载，无法进行配方差异分析")
        elif len(selected_products) < 2:
            st.info("请选择至少2个产品进行配方差异对比")
        else:
            # 获取所有选中产品的配方
            product_formulas = {}
            for product_id in selected_products:
                formula = parser.get_product_formula(product_id)
                if formula:
                    product_formulas[product_id] = formula
                else:
                    # 尝试清理后的ID
                    cleaned_id = parser.clean_product_id(product_id)
                    formula = parser.get_product_formula(cleaned_id)
                    if formula:
                        product_formulas[product_id] = formula
            
            if len(product_formulas) < 2:
                st.warning("未能获取足够的配方数据进行对比")
            else:
                # 选择基准产品
                base_product = st.selectbox(
                    "选择基准产品（其他产品将与此对比）",
                    options=list(product_formulas.keys()),
                    index=0
                )
                
                base_formula = product_formulas[base_product]
                
                # 显示基准配方
                with st.expander(f"📌 基准产品 {base_product} 的配方"):
                    st.write(f"**配方字符串**: {base_formula['formula_string']}")
                    st.write("**配方组成**:")
                    for layer, info in base_formula['layers'].items():
                        st.write(f"- {layer}: {info['code']} ({info['weight']}g)")
                        if info.get('components'):
                            for comp, percent in info['components'].items():
                                st.write(f"  - {comp}: {percent}%")
                
                st.markdown("---")
                
                # 对比其他产品
                for product_id in selected_products:
                    if product_id == base_product:
                        continue
                    
                    if product_id not in product_formulas:
                        st.warning(f"{product_id}: 未找到配方数据")
                        continue
                    
                    target_formula = product_formulas[product_id]
                    
                    # 使用配方解析器的对比功能
                    diff = parser.compare_two_formulas(base_formula, target_formula)
                    
                    with st.expander(f"📊 {product_id} vs {base_product}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**{product_id}配方**: {target_formula['formula_string']}")
                        
                        with col2:
                            if diff['differences']:
                                st.write(f"**发现 {len(diff['differences'])} 处差异**")
                            else:
                                st.success("配方完全相同")
                        
                        if diff['differences']:
                            st.write("**配方层级变化:**")
                            for d in diff['differences']:
                                if d['type'] == '新增':
                                    st.success(f"➕ {d['description']}")
                                elif d['type'] == '缺少':
                                    st.error(f"➖ {d['description']}")
                                elif d['type'] == '配方变化':
                                    st.info(f"🔄 {d['description']}")
                                elif d['type'] == '重量变化':
                                    st.warning(f"⚖️ {d['description']}")
                        
                        if diff.get('component_details'):
                            st.write("**成分具体变化:**")
                            for layer, changes in diff['component_details'].items():
                                if changes:
                                    st.write(f"***{layer}:***")
                                    
                                    # 创建成分变化表格
                                    change_data = []
                                    for change in changes:
                                        change_data.append({
                                            '成分': change['component'],
                                            '类型': change['type'],
                                            '变化量(g)': f"{change['change']:+.2f}",
                                            '说明': change['description']
                                        })
                                    
                                    if change_data:
                                        change_df = pd.DataFrame(change_data)
                                        st.dataframe(change_df, use_container_width=True, hide_index=True)
                        
                        # 总结主要差异
                        if diff['differences'] or diff.get('component_details'):
                            st.info("**差异总结**:")
                            
                            # 统计各类型差异
                            diff_types = {}
                            for d in diff['differences']:
                                diff_type = d['type']
                                if diff_type not in diff_types:
                                    diff_types[diff_type] = 0
                                diff_types[diff_type] += 1
                            
                            summary = []
                            if '配方变化' in diff_types:
                                summary.append(f"配方代码变化: {diff_types['配方变化']}处")
                            if '重量变化' in diff_types:
                                summary.append(f"重量调整: {diff_types['重量变化']}处")
                            if '新增' in diff_types:
                                summary.append(f"新增层级: {diff_types['新增']}个")
                            if '缺少' in diff_types:
                                summary.append(f"缺少层级: {diff_types['缺少']}个")
                            
                            for item in summary:
                                st.write(f"- {item}")
    
    with tab4:
        st.subheader(f"{title_prefix}性能指标对比")
        
        # 选择要对比的指标
        metrics = ['综合得分', '达标率(%)', '产氧时间(分钟)', '启动时长(秒)', 
                  '异常次数', '外壳最高温度(°C)']
        
        # 创建雷达图
        fig_radar = go.Figure()
        
        for sample_id in selected_products:
            sample_row = compare_df[compare_df['样品编号'] == sample_id]
            if sample_row.empty:
                continue
            sample_data = sample_row.iloc[0]
            
            # 准备雷达图数据（归一化到0-100）
            values = []
            for metric in metrics:
                if metric in sample_data:
                    val = sample_data[metric]
                    # 归一化处理
                    if metric == '综合得分':
                        normalized = val
                    elif metric == '达标率(%)':
                        normalized = val
                    elif metric == '产氧时间(分钟)':
                        normalized = min(val / 30 * 100, 100) if pd.notna(val) else 0
                    elif metric == '启动时长(秒)':
                        normalized = max(100 - val * 10, 0) if pd.notna(val) else 50
                    elif metric == '异常次数':
                        normalized = max(100 - val * 20, 0) if pd.notna(val) else 100
                    elif metric == '外壳最高温度(°C)':
                        normalized = max(100 - (val - 200) / 2, 0) if pd.notna(val) else 50
                    else:
                        normalized = 50
                    values.append(normalized)
                else:
                    values.append(0)
            
            fig_radar.add_trace(go.Scatterpolar(
                r=values,
                theta=metrics,
                fill='toself',
                name=sample_id
            ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=True,
            title=f"{title_prefix}性能指标雷达图",
            height=500
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
        
        # 柱状图对比
        st.subheader("关键指标柱状对比")
        
        # 选择要显示的指标
        selected_metric = st.selectbox(
            "选择指标",
            ['综合得分', '达标率(%)', '产氧时间(分钟)', '启动时长(秒)', 
             '异常次数', '外壳最高温度(°C)']
        )
        
        # 创建柱状图
        if selected_metric in compare_df.columns:
            fig_bar = px.bar(
                compare_df,
                x='样品编号',
                y=selected_metric,
                color='温度等级',
                title=f"{selected_metric}对比",
                text=selected_metric
            )
            
            fig_bar.update_traces(texttemplate='%{text:.1f}', textposition='outside')
            fig_bar.update_layout(height=400)
            
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning(f"数据中未找到 {selected_metric} 列")
    
    with tab5:
        st.subheader(f"{title_prefix}详细数据对比")
        
        # 转置数据以便对比
        compare_transposed = compare_df.set_index('样品编号').T
        st.dataframe(compare_transposed, use_container_width=True)
        
        # 下载按钮
        csv = compare_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 下载对比数据",
            data=csv,
            file_name=f'{title_prefix}对比结果.csv',
            mime='text/csv'
        )

# 加载数据
ranking_df, stats_df, timestamp = load_data()

if ranking_df is None:
    st.error("❌ 未找到数据文件")
    st.info("""
    请确保已经运行过分析程序：
    1. python 简单分析程序.py
    2. python 评分排名程序.py
    3. python 对比分析程序.py
    """)
    st.stop()

# 主页
if page == "主页":
    st.header("🏠 欢迎使用氧烛分析系统")
    
    # 关键指标卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("样品总数", f"{len(ranking_df)} 个")
    
    with col2:
        avg_score = ranking_df['综合得分'].mean()
        st.metric("平均得分", f"{avg_score:.1f} 分")
    
    with col3:
        best = ranking_df.iloc[0]
        st.metric("最高分", f"{best['综合得分']:.1f} 分", f"{best['样品编号']}")
    
    with col4:
        a_grade = len(ranking_df[ranking_df['评级'].str.contains('A级')])
        st.metric("A级样品", f"{a_grade} 个")
    
    st.markdown("---")
    
    # 快速统计
    st.subheader("📈 快速统计")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 温度等级分布
        temp_counts = ranking_df['温度等级'].value_counts()
        fig = px.pie(values=temp_counts.values, names=temp_counts.index, 
                     title="温度等级分布")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # 评级分布
        grade_counts = ranking_df['评级'].value_counts()
        fig = px.bar(x=grade_counts.index, y=grade_counts.values,
                     title="评级分布", labels={'x': '评级', 'y': '数量'})
        st.plotly_chart(fig, use_container_width=True)

# 数据总览
elif page == "数据总览":
    st.header("📋 数据总览")
    
    # 筛选器
    col1, col2, col3 = st.columns(3)
    
    with col1:
        temp_filter = st.multiselect(
            "选择温度等级",
            options=ranking_df['温度等级'].unique(),
            default=ranking_df['温度等级'].unique()
        )
    
    with col2:
        min_score = st.slider("最低分数", 0, 100, 0)
    
    with col3:
        sort_by = st.selectbox("排序方式", ["综合得分", "达标率(%)", "样品编号"])
    
    # 筛选数据
    filtered_df = ranking_df[
        (ranking_df['温度等级'].isin(temp_filter)) &
        (ranking_df['综合得分'] >= min_score)
    ]
    
    # 排序
    if sort_by == "综合得分":
        filtered_df = filtered_df.sort_values('综合得分', ascending=False)
    elif sort_by == "达标率(%)":
        filtered_df = filtered_df.sort_values('达标率(%)', ascending=False)
    else:
        filtered_df = filtered_df.sort_values('样品编号')
    
    # 显示表格
    st.dataframe(filtered_df, use_container_width=True, height=500)
    
    # 下载按钮
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 下载CSV",
        data=csv,
        file_name='筛选结果.csv',
        mime='text/csv'
    )

# 排名分析
elif page == "排名分析":
    st.header("🏆 排名分析")
    
    # TOP N 选择
    n = st.slider("显示前N名", 5, 20, 10)
    
    top_n = ranking_df.head(n)
    
    # 创建柱状图
    fig = go.Figure()
    
    # 根据温度等级着色
    colors = []
    for temp in top_n['温度等级']:
        if temp == '低温':
            colors.append('#4ECDC4')
        elif temp == '常温':
            colors.append('#FF6B6B')
        elif temp == '高温':
            colors.append('#45B7D1')
        else:
            colors.append('#96CEB4')
    
    fig.add_trace(go.Bar(
        x=top_n['样品编号'],
        y=top_n['综合得分'],
        marker_color=colors,
        text=top_n['综合得分'].round(1),
        textposition='outside'
    ))
    
    fig.update_layout(
        title=f"TOP {n} 样品排名",
        xaxis_title="样品编号",
        yaxis_title="综合得分",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 显示详细信息
    st.subheader(f"📊 TOP {n} 详细数据")
    st.dataframe(top_n[['排名', '样品编号', '温度等级', '综合得分', '评级']])

# 对比分析（自定义）
elif page == "对比分析":
    st.header("📊 自定义对比分析")
    
    # 选择要对比的样品
    selected = st.multiselect(
        "选择要对比的样品（最多8个）",
        options=ranking_df['样品编号'].tolist(),
        default=ranking_df.head(3)['样品编号'].tolist()
    )
    
    if len(selected) > 8:
        st.warning("最多选择8个样品")
        selected = selected[:8]
    
    if selected:
        show_comparison_component(selected, ranking_df, "")

# 配方组对比
elif page == "配方组对比":
    st.header("🧪 相同配方产品对比")
    
    # 获取配方解析器
    parser = get_formula_parser()
    
    if not parser:
        st.warning("""
        ⚠️ 配方解析模块未加载。请确保：
        1. 配方表.xlsx 文件在 data 目录
        2. formula_parser.py 在 modules 目录
        """)
    else:
        # 选择是否包含单个产品的配方组
        include_single = st.checkbox("显示只有单个产品的配方组（新配方）", value=True)
        
        # 按配方分组，根据选择决定是否包含单个产品的组
        formula_groups = group_products_by_formula(ranking_df, parser, include_single=include_single)
        
        if not formula_groups:
            st.info("未找到配方组")
        else:
            # 分离单个产品和多个产品的配方组
            single_product_groups = {k: v for k, v in formula_groups.items() if len(v) == 1}
            multi_product_groups = {k: v for k, v in formula_groups.items() if len(v) > 1}
            
            # 显示统计信息
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("配方组总数", len(formula_groups))
            with col2:
                st.metric("多产品配方组", len(multi_product_groups))
            with col3:
                st.metric("单产品配方组（新配方）", len(single_product_groups))
            
            st.markdown("---")
            
            # 选择配方组
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 准备选项
                options = []
                
                # 先添加多产品配方组
                for formula, products in multi_product_groups.items():
                    display_formula = formula if len(formula) <= 50 else formula[:50] + "..."
                    option_text = f"【多产品】{display_formula} ({len(products)}个产品)"
                    options.append((option_text, formula, products, False))
                
                # 再添加单产品配方组（如果选择显示）
                if include_single:
                    for formula, products in single_product_groups.items():
                        display_formula = formula if len(formula) <= 50 else formula[:50] + "..."
                        option_text = f"【新配方】{display_formula} (仅{products[0]})"
                        options.append((option_text, formula, products, True))
                
                if options:
                    # 选择配方
                    selected_option = st.selectbox(
                        "选择配方组",
                        options=range(len(options)),
                        format_func=lambda x: options[x][0]
                    )
                    
                    selected_formula = options[selected_option][1]
                    selected_products = options[selected_option][2]
                    is_single = options[selected_option][3]
                else:
                    st.warning("没有可选的配方组")
                    st.stop()
            
            with col2:
                if is_single:
                    st.info(f"""
                    **新配方产品**
                    - 产品编号: {selected_products[0]}
                    - 配方: {selected_formula[:30]}...
                    - 建议: 可与其他产品对比
                    """)
                else:
                    st.info(f"""
                    **配方详情**
                    - 产品数量: {len(selected_products)}个
                    - 配方: {selected_formula[:30]}...
                    """)
            
            # 显示该配方组的产品列表
            st.subheader("📋 该配方组包含的产品")
            
            # 获取这些产品的数据
            group_df = ranking_df[ranking_df['样品编号'].isin(selected_products)]
            group_df = group_df.sort_values('综合得分', ascending=False)
            
            # 显示产品概览
            if not is_single:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("平均得分", f"{group_df['综合得分'].mean():.1f}分")
                with col2:
                    st.metric("最高得分", f"{group_df['综合得分'].max():.1f}分")
                with col3:
                    st.metric("最低得分", f"{group_df['综合得分'].min():.1f}分")
            else:
                # 单个产品显示其详细信息
                product_data = group_df.iloc[0]
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("综合得分", f"{product_data['综合得分']:.1f}分")
                with col2:
                    st.metric("达标率", f"{product_data.get('达标率(%)', 0):.1f}%")
                with col3:
                    st.metric("产氧时间", f"{product_data.get('产氧时间(分钟)', 0):.1f}分钟")
                with col4:
                    st.metric("异常次数", f"{product_data.get('异常次数', 0):.0f}次")
            
            # 显示产品表格
            display_cols = ['排名', '样品编号', '温度等级', '综合得分', '达标率(%)', 
                          '产氧时间(分钟)', '异常次数', '评级']
            available_cols = [col for col in display_cols if col in group_df.columns]
            
            st.dataframe(
                group_df[available_cols].reset_index(drop=True),
                use_container_width=True
            )
            
            # 如果是单个产品，提供与其他产品对比的选项
            if is_single:
                st.subheader("🔄 与其他产品对比")
                st.info("该配方只有一个产品，您可以选择其他产品进行对比分析")
                
                # 选择其他产品进行对比
                other_products = ranking_df[ranking_df['样品编号'] != selected_products[0]]['样品编号'].tolist()
                
                compare_with = st.multiselect(
                    f"选择要与 {selected_products[0]} 对比的产品",
                    options=other_products,
                    default=other_products[:min(2, len(other_products))] if other_products else []
                )
                
                if compare_with:
                    products_to_compare = selected_products + compare_with
                    # 使用通用对比组件
                    show_comparison_component(
                        products_to_compare, 
                        ranking_df, 
                        f"新配方 {selected_formula[:30]}... 对比分析 - "
                    )
            
            else:
                # 分析温度等级的影响（只对多产品配方组有意义）
                st.subheader("🌡️ 温度等级对配方性能的影响")
                
                # 按温度等级分组统计
                temp_analysis = group_df.groupby('温度等级').agg({
                    '综合得分': ['mean', 'std', 'count'],
                    '达标率(%)': 'mean',
                    '异常次数': 'mean'
                }).round(2)
                
                if not temp_analysis.empty:
                    # 重命名列
                    temp_analysis.columns = ['平均得分', '得分标准差', '样品数', '平均达标率', '平均异常次数']
                    st.dataframe(temp_analysis)
                    
                    # 可视化温度等级影响
                    fig = px.box(
                        group_df,
                        x='温度等级',
                        y='综合得分',
                        title="不同温度等级下的得分分布",
                        points="all"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                # 选择要详细对比的产品
                st.subheader("🔍 详细对比分析")
                
                # 自动选择或手动选择
                auto_select = st.checkbox("自动选择各温度等级最佳产品", value=True)
                
                if auto_select:
                    # 自动选择每个温度等级的最佳产品
                    products_to_compare = []
                    for temp in group_df['温度等级'].unique():
                        temp_best = group_df[group_df['温度等级'] == temp].iloc[0]
                        products_to_compare.append(temp_best['样品编号'])
                    
                    st.info(f"已自动选择各温度等级最佳产品: {', '.join(products_to_compare)}")
                else:
                    # 手动选择
                    products_to_compare = st.multiselect(
                        "选择要对比的产品",
                        options=selected_products,
                        default=selected_products[:min(4, len(selected_products))]
                    )
                
                if products_to_compare and len(products_to_compare) > 1:
                    # 使用通用对比组件
                    show_comparison_component(
                        products_to_compare, 
                        ranking_df, 
                        f"配方 {selected_formula[:30]}... "
                    )
                elif len(products_to_compare) == 1:
                    st.warning("请至少选择2个产品进行对比")

# 最佳配方
elif page == "最佳配方":
    st.header("🏅 最佳配方推荐")
    
    # 各温度等级最佳
    st.subheader("🌡️ 各温度等级最佳样品")
    
    best_by_temp = []
    for temp in ranking_df['温度等级'].unique():
        temp_df = ranking_df[ranking_df['温度等级'] == temp]
        if not temp_df.empty:
            best = temp_df.iloc[0]
            best_by_temp.append({
                '温度等级': temp,
                '最佳样品': best['样品编号'],
                '综合得分': best['综合得分'],
                '评级': best['评级']
            })
    
    best_temp_df = pd.DataFrame(best_by_temp)
    st.dataframe(best_temp_df, use_container_width=True)
    
    # 总体最佳
    st.subheader("🏆 总体最佳TOP 5")
    
    top5 = ranking_df.head(5)
    
    for idx, row in top5.iterrows():
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(f"第{row['排名']}名", row['样品编号'])
        with col2:
            st.metric("得分", f"{row['综合得分']:.1f}")
        with col3:
            st.metric("温度等级", row['温度等级'])
        with col4:
            st.metric("评级", row['评级'])
        
        st.markdown("---")
    
    # 配方统计（如果有配方解析器）
    parser = get_formula_parser()
    if parser:
        st.subheader("📊 配方性能统计")
        
        # 统计每个配方的平均得分
        formula_scores = {}
        for idx, row in ranking_df.iterrows():
            formula = extract_formula_from_id(row['样品编号'], parser)
            if formula:
                if formula not in formula_scores:
                    formula_scores[formula] = []
                formula_scores[formula].append(row['综合得分'])
        
        # 计算平均分
        formula_avg = []
        for formula, scores in formula_scores.items():
            formula_avg.append({
                '配方': formula[:50] + "..." if len(formula) > 50 else formula,
                '样品数': len(scores),
                '平均得分': np.mean(scores),
                '最高分': max(scores),
                '最低分': min(scores),
                '标准差': np.std(scores)
            })
        
        formula_avg_df = pd.DataFrame(formula_avg)
        formula_avg_df = formula_avg_df.sort_values('平均得分', ascending=False)
        
        st.dataframe(formula_avg_df.head(10), use_container_width=True)
    
    # 改进建议
    st.subheader("💡 优化建议")
    
    # 分析各温度组
    lt_df = ranking_df[ranking_df['温度等级'] == '低温']
    mt_df = ranking_df[ranking_df['温度等级'] == '常温']
    ht_df = ranking_df[ranking_df['温度等级'] == '高温']
    std_df = ranking_df[ranking_df['温度等级'] == '未注明']
    
    suggestions = []
    
    if not mt_df.empty and mt_df['综合得分'].mean() > 75:
        suggestions.append("✅ 常温工艺表现优秀，建议作为主要生产工艺")
    
    if not lt_df.empty and lt_df['综合得分'].mean() < 70:
        suggestions.append("⚠️ 低温工艺需要改进，平均得分偏低")
    
    if not ht_df.empty and ht_df['综合得分'].mean() > 80:
        suggestions.append("✅ 高温工艺稳定性好，可作为备选方案")
    
    best_overall = ranking_df.iloc[0]
    suggestions.append(f"🏆 最佳配方是 {best_overall['样品编号']}（{best_overall['温度等级']}），建议深入研究")
    
    for suggestion in suggestions:
        st.info(suggestion)

# 高级分析模块
elif page == "高级分析":
    st.header("🔬 高级分析模块")
    
    # 导入高级分析模块
    try:
        from modules.advanced_analysis import (
            KineticsAnalyzer, 
            SPCController,
            MLPredictor,
            FaultDiagnosticSystem,
            DOEDesigner,
            CostAnalyzer
        )
        modules_loaded = True
    except ImportError as e:
        st.error(f"""
        ⚠️ 高级分析模块未正确安装
        
        请执行以下步骤：
        1. 创建目录: mkdir -p modules/advanced_analysis
        2. 添加模块文件
        3. 安装依赖: pip install scipy plotly scikit-learn pyDOE2 joblib
        
        错误信息: {e}
        """)
        modules_loaded = False
        st.stop()
    
    # 创建6个标签页
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "⚗️ 反应动力学", 
        "📊 批次一致性(SPC)", 
        "🤖 机器学习预测",
        "🔧 故障诊断",
        "🧪 DOE实验设计",
        "💰 成本分析"
    ])

    with tab1:
        st.subheader("⚗️ 反应动力学分析")

        # 选择样品 - 注意这里不使用key参数，或使用不同的key
        selected_sample = st.selectbox(
            "选择样品进行分析",
            ranking_df['样品编号'].tolist()
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"""
            **反应动力学分析**将计算：
            - 反应速率和加速度
            - 反应阶段划分（诱导期、加速期、稳定期、衰减期）
            - 反应级数和速率常数
            - 速率变化与产氧量关系
            - 活化能（如有温度数据）
            - AS9100D合规性检查
            """)

        with col2:
            analyze_button = st.button("🚀 开始分析", key="analyze_kinetics")

        if analyze_button:
            # 加载流量数据
            flow_data, _ = load_flow_data(selected_sample)
            # 加载基准曲线
            baseline_df = load_baseline()

            if flow_data is not None:
                # 创建分析器
                analyzer = KineticsAnalyzer()

                # 执行分析
                with st.spinner("正在进行动力学分析..."):
                    try:
                        # 检查是否有温度数据
                        temp_data = None
                        if all(col in flow_data.columns for col in ['CH1', 'CH2', 'CH3']):
                            temp_data = flow_data[['CH1', 'CH2', 'CH3']].mean(axis=1).values

                        # 执行分析（传入基准数据）
                        results = analyzer.analyze(flow_data, temperature_data=temp_data, baseline_data=baseline_df)

                        # 保存结果到 session_state
                        st.session_state.kinetics_results = results
                        st.session_state.kinetics_sample = selected_sample  # 保存分析时的样品名
                        st.success("✅ 分析完成！")
                    except Exception as e:
                        st.error(f"分析失败: {e}")
                        st.session_state.kinetics_results = None
            else:
                st.warning("未找到该样品的流量数据")

        # ========== 独立的结果显示部分（在按钮if块外面） ==========
        # 检查是否有结果且是当前选择的样品
        if 'kinetics_results' in st.session_state and st.session_state.kinetics_results is not None:
            if 'kinetics_sample' in st.session_state and st.session_state.kinetics_sample == selected_sample:
                results = st.session_state.kinetics_results

                # 关键指标卡片
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric(
                        "最大反应速率",
                        f"{results['max_reaction_rate']:.3f} L/min²",
                        f"@ {results['max_rate_time']:.1f}s"
                    )

                with col2:
                    st.metric(
                        "反应级数",
                        results.get('reaction_order_model', '-'),
                        f"R² = {results.get('model_R2', 0):.3f}"
                    )

                with col3:
                    if results.get('apparent_reaction_order'):
                        st.metric(
                            "表观反应级数",
                            f"{results['apparent_reaction_order']:.2f}"
                        )
                    else:
                        st.metric("表观反应级数", "N/A")

                with col4:
                    compliance = results['AS9100D合规性']
                    status_color = "🟢" if compliance['status'] == 'PASS' else "🔴"
                    st.metric("AS9100D", f"{status_color} {compliance['status']}")

                # 反应阶段表
                st.subheader("📊 反应阶段划分")
                phases_df = pd.DataFrame(results['反应阶段'])
                st.dataframe(phases_df, use_container_width=True)

                # 增强的反应动力学曲线图
                st.subheader("📈 反应动力学曲线")

                # 添加图表控制选项
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.session_state.display_mode = st.selectbox(
                        "显示模式",
                        ["标准视图", "对数坐标", "聚焦稳定期"],
                        key="kinetics_display_mode",
                        index=["标准视图", "对数坐标", "聚焦稳定期"].index(st.session_state.display_mode),
                        help="选择不同的视图模式查看数据"
                    )

                with col2:
                    st.session_state.zoom_level = st.slider(
                        "Y轴缩放",
                        min_value=50,
                        max_value=300,
                        value=st.session_state.zoom_level,
                        key="kinetics_zoom_slider",
                        step=10,
                        format="%d%%",
                        help="100%=数据实际范围，200%=缩小一倍，50%=放大一倍"
                    )

                with col3:
                    st.session_state.show_time_range = st.checkbox(
                        "自定义时间范围",
                        value=st.session_state.show_time_range,
                        key="kinetics_time_range_check"
                    )

                # 如果选择自定义时间范围，显示滑块
                if st.session_state.show_time_range:
                    time_min = float(results['时间数据'][0])
                    time_max = float(results['时间数据'][-1])
                    time_range = st.slider(
                        "选择时间范围（秒）",
                        min_value=time_min,
                        max_value=time_max,
                        value=(time_min, time_max),
                        step=10.0,
                        format="%.0f秒"
                    )
                else:
                    time_range = None

                # 根据选择设置参数
                use_log_scale = (st.session_state.display_mode == "对数坐标")
                zoom_stable = (st.session_state.display_mode == "聚焦稳定期")

                # 创建子图
                fig = make_subplots(
                    rows=2, cols=1,
                    subplot_titles=("流量曲线与基准对比", "反应速率与累计产氧量"),
                    shared_xaxes=True,
                    vertical_spacing=0.12,
                    specs=[[{"secondary_y": False}],
                           [{"secondary_y": True}]]
                )

                # ========== 图1：流量曲线与基准对比 ==========
                # 实际流量曲线
                fig.add_trace(
                    go.Scatter(
                        x=results['时间数据'],
                        y=results['流量数据'],
                        mode='lines',
                        name='实际流量',
                        line=dict(color='blue', width=2),
                        hovertemplate='时间: %{x:.1f}s<br>流量: %{y:.2f} L/min<extra></extra>'
                    ),
                    row=1, col=1
                )

                # 基准曲线（黄色虚线）
                if results.get('基准时间') is not None and results.get('基准流量') is not None:
                    fig.add_trace(
                        go.Scatter(
                            x=results['基准时间'],
                            y=results['基准流量'],
                            mode='lines',
                            name='基准曲线',
                            line=dict(color='gold', width=2, dash='dash'),
                            hovertemplate='时间: %{x:.1f}s<br>基准: %{y:.2f} L/min<extra></extra>'
                        ),
                        row=1, col=1
                    )

                # ========== 图2：反应速率与累计产氧量 ==========
                # 准备数据
                time_data = np.array(results['时间数据'])
                rate_data = np.array(results['reaction_rate'])
                oxygen_data = np.array(results['累计产氧量'])

                # 根据显示模式调整数据
                if zoom_stable:
                    # 聚焦稳定期（100-1200秒）
                    mask = (time_data >= 100) & (time_data <= 1200)
                    display_time = time_data[mask]
                    display_rate = rate_data[mask]
                    display_oxygen = oxygen_data[mask]
                elif st.session_state.show_time_range and time_range:
                    # 自定义时间范围
                    mask = (time_data >= time_range[0]) & (time_data <= time_range[1])
                    display_time = time_data[mask]
                    display_rate = rate_data[mask]
                    display_oxygen = oxygen_data[mask]
                else:
                    display_time = time_data
                    display_rate = rate_data
                    display_oxygen = oxygen_data

                # 反应速率曲线
                if use_log_scale:
                    # 对数坐标需要处理负值
                    display_rate_plot = np.abs(display_rate)
                    rate_name = '反应速率(绝对值)'
                else:
                    display_rate_plot = display_rate
                    rate_name = '反应速率'

                fig.add_trace(
                    go.Scatter(
                        x=display_time,
                        y=display_rate_plot,
                        mode='lines',
                        name=rate_name,
                        line=dict(color='red', width=2),
                        hovertemplate='时间: %{x:.1f}s<br>速率: %{y:.3f} L/min²<extra></extra>'
                    ),
                    row=2, col=1,
                    secondary_y=False
                )

                # 累计产氧量曲线
                fig.add_trace(
                    go.Scatter(
                        x=display_time,
                        y=display_oxygen,
                        mode='lines',
                        name='累计产氧量',
                        line=dict(color='green', width=2, dash='dot'),
                        hovertemplate='时间: %{x:.1f}s<br>产氧: %{y:.1f} L<extra></extra>'
                    ),
                    row=2, col=1,
                    secondary_y=True
                )

                # 更新轴标签和布局
                fig.update_xaxes(title_text="时间 (秒)", row=2, col=1)
                fig.update_yaxes(title_text="流量 (L/min)", row=1, col=1)

                if use_log_scale:
                    fig.update_yaxes(
                        type="log",
                        title_text="反应速率 (L/min², 对数坐标)",
                        row=2, col=1,
                        secondary_y=False
                    )
                else:
                    fig.update_yaxes(
                        title_text="反应速率 (L/min²)",
                        row=2, col=1,
                        secondary_y=False
                    )

                fig.update_yaxes(
                    title_text="累计产氧量 (L)",
                    row=2, col=1,
                    secondary_y=True
                )

                # 设置时间轴范围
                if st.session_state.show_time_range and time_range:
                    fig.update_xaxes(range=time_range, row=1, col=1)
                    fig.update_xaxes(range=time_range, row=2, col=1)
                elif zoom_stable:
                    fig.update_xaxes(range=[100, 1200], row=1, col=1)
                    fig.update_xaxes(range=[100, 1200], row=2, col=1)

                # 更新布局
                fig.update_layout(
                    height=700,
                    showlegend=True,
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )

                st.plotly_chart(fig, use_container_width=True)

                # 添加快速缩放按钮
                st.markdown("**快速缩放**")
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    if st.button("放大", key="zoom_in"):
                        st.session_state.zoom_level = max(50, st.session_state.zoom_level - 25)
                        st.rerun()
                with col2:
                    if st.button("实际大小", key="zoom_100"):
                        st.session_state.zoom_level = 100
                        st.rerun()
                with col3:
                    if st.button("缩小", key="zoom_out"):
                        st.session_state.zoom_level = min(300, st.session_state.zoom_level + 25)
                        st.rerun()
                with col4:
                    if st.button("全览", key="zoom_all"):
                        st.session_state.zoom_level = 50
                        st.session_state.display_mode = "标准视图"
                        st.rerun()
                with col5:
                    if st.button("重置", key="zoom_reset"):
                        st.session_state.zoom_level = 100
                        st.session_state.display_mode = "标准视图"
                        st.session_state.show_time_range = False
                        st.rerun()

            # 速率变化与产氧量关系分析（继续显示其他分析结果）
            st.subheader("🔍 速率变化与产氧量关系")

            if '关键点分析' in results:
                # 显示关键点表格
                key_points_df = pd.DataFrame(results['关键点分析'])
                # 格式化数值
                for col in ['时间(s)', '累计产氧量(L)', '反应速率(L/min²)', '流量(L/min)']:
                    if col in key_points_df.columns:
                        key_points_df[col] = key_points_df[col].round(2)

                st.dataframe(key_points_df, use_container_width=True)

                # 产氧效率分析
                col1, col2, col3 = st.columns(3)

                with col1:
                    total_oxygen = results['累计产氧量'][-1]
                    st.metric("总产氧量", f"{total_oxygen:.1f} L")

                with col2:
                    # 计算前半程产氧效率
                    half_time_idx = len(results['累计产氧量']) // 2
                    half_oxygen = results['累计产氧量'][half_time_idx]
                    efficiency = (half_oxygen / total_oxygen) * 100
                    st.metric("前半程产氧效率", f"{efficiency:.1f}%")

                with col3:
                    # 计算平均产氧速率
                    total_time = results['时间数据'][-1] / 60  # 转换为分钟
                    avg_rate = total_oxygen / total_time if total_time > 0 else 0
                    st.metric("平均产氧速率", f"{avg_rate:.2f} L/min")

            # 合规性详情
            if compliance.get('issues') or compliance.get('warnings'):
                st.subheader("⚠️ 合规性问题")
                for issue in compliance.get('issues', []):
                    st.error(f"❌ {issue}")
                for warning in compliance.get('warnings', []):
                    st.warning(f"⚠️ {warning}")

            # 下载报告
            # 重新创建analyzer实例来生成报告
            from modules.advanced_analysis import KineticsAnalyzer

            temp_analyzer = KineticsAnalyzer()
            report = temp_analyzer.generate_kinetics_report(results)
            st.download_button(
                label="📥 下载动力学分析报告",
                data=report,
                file_name=f"{selected_sample}_动力学分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    
    with tab2:
        st.subheader("📊 批次一致性分析（SPC）")
        
        # 选择分析方式
        analysis_mode = st.radio(
            "选择分析方式",
            ["按配方组", "按温度等级", "自定义选择"],
            horizontal=True
        )
        
        selected_products = []
        group_name = ""
        
        if analysis_mode == "按配方组":
            parser = get_formula_parser()
            if parser:
                formula_groups = group_products_by_formula(ranking_df, parser)
                if formula_groups:
                    # 只显示有多个产品的配方组
                    multi_groups = {k: v for k, v in formula_groups.items() if len(v) > 1}
                    if multi_groups:
                        selected_formula = st.selectbox(
                            "选择配方组",
                            list(multi_groups.keys()),
                            format_func=lambda x: f"{x[:50]}... ({len(multi_groups[x])}个产品)"
                        )
                        selected_products = multi_groups[selected_formula]
                        group_name = f"配方_{selected_formula[:20]}"
                    else:
                        st.warning("没有包含多个产品的配方组")
                else:
                    st.warning("未找到配方组数据")
            else:
                st.warning("配方解析模块未加载")
        
        elif analysis_mode == "按温度等级":
            temp_level = st.selectbox(
                "选择温度等级",
                ranking_df['温度等级'].unique()
            )
            selected_products = ranking_df[ranking_df['温度等级'] == temp_level]['样品编号'].tolist()
            group_name = f"温度等级_{temp_level}"
        
        else:  # 自定义选择
            selected_products = st.multiselect(
                "选择要分析的产品（至少3个）",
                ranking_df['样品编号'].tolist()
            )
            group_name = "自定义组"
        
        if selected_products and len(selected_products) >= 3:
            st.info(f"已选择 {len(selected_products)} 个产品进行批次分析")
            
            if st.button("🚀 开始SPC分析", key="start_spc"):
                # 获取批次数据
                batch_data = ranking_df[ranking_df['样品编号'].isin(selected_products)].copy()
                
                # 创建SPC控制器
                spec_limits = {
                    '产氧时间': {'LSL': 22, 'USL': 40, 'target': 25},
                    '达标率': {'LSL': 95, 'USL': 100, 'target': 100},
                    '外壳最高温度': {'LSL': None, 'USL': 230, 'target': 180},
                    '启动时长': {'LSL': None, 'USL': 2, 'target': 1},
                    '达峰时长': {'LSL': None, 'USL': 10, 'target': 5}
                }
                
                spc = SPCController(spec_limits)
                
                # 执行分析
                with st.spinner("正在进行SPC分析..."):
                    try:
                        results = spc.analyze_batch_consistency(batch_data)
                        
                        st.success("✅ SPC分析完成！")
                        
                        # AS9100D合规性
                        compliance = results['AS9100D合规性']
                        status_colors = {"PASS": "🟢", "WARNING": "🟡", "FAIL": "🔴"}
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "AS9100D合规性", 
                                f"{status_colors[compliance['overall_status']]} {compliance['overall_status']}"
                            )
                        with col2:
                            in_control = sum(1 for c in results['控制图'].values() if c['in_control'])
                            total = len(results['控制图'])
                            st.metric("受控过程", f"{in_control}/{total}")
                        with col3:
                            st.metric("批次数", len(batch_data))
                        
                        # 过程能力表
                        st.subheader("📊 过程能力指数")
                        
                        capability_data = []
                        for metric, cap in results.get('过程能力', {}).items():
                            row = {
                                '指标': metric,
                                'Cpk': cap.get('Cpk', '-'),
                                'Cp': cap.get('Cp', '-'),
                                'PPM': cap.get('PPM', '-'),
                                'Sigma Level': cap.get('Sigma_Level', '-')
                            }
                            
                            # 判断状态
                            cpk = cap.get('Cpk')
                            if cpk and isinstance(cpk, (int, float)):
                                if cpk >= 1.33:
                                    row['状态'] = '✅ 优秀'
                                elif cpk >= 1.0:
                                    row['状态'] = '⚠️ 合格'
                                else:
                                    row['状态'] = '❌ 不合格'
                            else:
                                row['状态'] = '-'
                            
                            capability_data.append(row)
                        
                        if capability_data:
                            cap_df = pd.DataFrame(capability_data)
                            st.dataframe(cap_df, use_container_width=True, hide_index=True)
                        
                        # 控制图
                        st.subheader("📈 控制图")
                        
                        if results.get('控制图'):
                            metric_to_plot = st.selectbox(
                                "选择指标查看控制图",
                                list(results['控制图'].keys())
                            )
                            
                            if metric_to_plot:
                                chart_data = results['控制图'][metric_to_plot]
                                
                                # 构建列名
                                col_mapping = {
                                    '产氧时间': '产氧时间(分钟)',
                                    '达标率': '达标率(%)',
                                    '外壳最高温度': '外壳最高温度(°C)',
                                    '启动时长': '启动时长(秒)',
                                    '达峰时长': '达峰时长(秒)'
                                }
                                
                                metric_col = col_mapping.get(metric_to_plot, metric_to_plot)
                                
                                if metric_col in batch_data.columns:
                                    data_points = batch_data[metric_col].dropna().values
                                    
                                    # 创建控制图
                                    fig = go.Figure()
                                    
                                    # 数据点
                                    fig.add_trace(go.Scatter(
                                        y=data_points,
                                        mode='lines+markers',
                                        name='测量值',
                                        line=dict(color='blue'),
                                        marker=dict(size=8)
                                    ))
                                    
                                    # 控制限
                                    fig.add_hline(
                                        y=chart_data['mean'], 
                                        line_dash="dash",
                                        line_color="green", 
                                        annotation_text=f"CL={chart_data['mean']:.2f}"
                                    )
                                    fig.add_hline(
                                        y=chart_data['UCL'], 
                                        line_dash="dash",
                                        line_color="red", 
                                        annotation_text=f"UCL={chart_data['UCL']:.2f}"
                                    )
                                    fig.add_hline(
                                        y=chart_data['LCL'], 
                                        line_dash="dash",
                                        line_color="red", 
                                        annotation_text=f"LCL={chart_data['LCL']:.2f}"
                                    )
                                    
                                    # 标记失控点
                                    if chart_data.get('out_of_control'):
                                        ooc_indices = [p['index'] for p in chart_data['out_of_control'] 
                                                     if isinstance(p, dict) and 'index' in p]
                                        if ooc_indices:
                                            ooc_values = [data_points[i] for i in ooc_indices 
                                                        if i < len(data_points)]
                                            if ooc_values:
                                                fig.add_trace(go.Scatter(
                                                    x=ooc_indices,
                                                    y=ooc_values,
                                                    mode='markers',
                                                    name='失控点',
                                                    marker=dict(
                                                        color='red', 
                                                        size=12, 
                                                        symbol='x'
                                                    )
                                                ))
                                    
                                    fig.update_layout(
                                        title=f"{metric_to_plot} 控制图",
                                        xaxis_title="批次序号",
                                        yaxis_title=metric_to_plot,
                                        height=400,
                                        hovermode='x unified'
                                    )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    # 失控信息
                                    if not chart_data['in_control']:
                                        st.warning(f"⚠️ 发现失控点，过程不稳定")
                        
                        # 改进建议
                        if compliance.get('required_actions'):
                            st.subheader("📋 必需的改进措施")
                            for action in compliance['required_actions']:
                                st.write(f"• {action}")
                        
                        # 下载报告
                        html_report = spc.generate_spc_report(results)
                        st.download_button(
                            label="📥 下载SPC分析报告",
                            data=html_report,
                            file_name=f"SPC分析_{group_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                            mime="text/html"
                        )
                        
                    except Exception as e:
                        st.error(f"SPC分析失败: {e}")
                        st.exception(e)
        
        elif selected_products:
            st.warning("⚠️ 至少需要3个产品才能进行SPC分析")
        else:
            st.info("👆 请选择要分析的产品")
    
    with tab3:
        st.subheader("🤖 机器学习预测")
        
        # 选择模型类型
        model_type = st.selectbox(
            "选择模型类型",
            ["random_forest", "gradient_boost", "gaussian_process"],
            format_func=lambda x: {
                'random_forest': '随机森林',
                'gradient_boost': '梯度提升',
                'gaussian_process': '高斯过程'
            }[x]
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎯 训练模型"):
                predictor = MLPredictor(model_type=model_type)
                
                with st.spinner("正在训练模型..."):
                    try:
                        # 使用现有数据训练
                        train_result = predictor.train(ranking_df, target_column='综合得分')
                        
                        if train_result['status'] == 'SUCCESS':
                            st.success("✅ 模型训练成功！")
                            
                            # 显示训练结果
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("R²", f"{train_result['train_r2']:.4f}")
                            with col2:
                                st.metric("交叉验证R²", f"{train_result['cv_r2_mean']:.4f}")
                            with col3:
                                st.metric("样本数", train_result['n_samples'])
                            
                            # 特征重要性
                            if train_result.get('feature_importance') is not None:
                                st.subheader("📊 特征重要性")
                                fig = px.bar(
                                    train_result['feature_importance'].head(10),
                                    x='importance',
                                    y='feature',
                                    orientation='h',
                                    title="Top 10 重要特征"
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # 保存模型到session_state
                            st.session_state['ml_model'] = predictor
                        else:
                            st.error(f"训练失败: {train_result['message']}")
                    except Exception as e:
                        st.error(f"训练出错: {e}")

        with col2:
            # 目标得分滑块（放在按钮外面，这样不会因为按钮点击而重新创建）
            target_score = st.slider(
                "目标得分",
                70, 100,
                st.session_state.target_score_ml,
                key="ml_target_score_slider"
            )
            st.session_state.target_score_ml = target_score

            # 配方优化按钮
            if st.button("🔮 配方优化建议"):
                if 'ml_model' in st.session_state:
                    predictor = st.session_state['ml_model']

                    with st.spinner("正在优化配方..."):
                        try:
                            optimization = predictor.optimize_formula(
                                target_score=st.session_state.target_score_ml,  # 使用session_state中的值
                                n_suggestions=3
                            )

                            if optimization['status'] == 'SUCCESS':
                                st.session_state.ml_optimization_result = optimization
                                st.session_state.ml_target_score_used = st.session_state.target_score_ml
                                st.success("✅ 优化完成！")
                            else:
                                st.error(f"优化失败: {optimization.get('message', '未知错误')}")
                                st.session_state.ml_optimization_result = None

                        except Exception as e:
                            st.error(f"优化出错: {str(e)}")
                            st.exception(e)  # 显示详细错误信息
                            st.session_state.ml_optimization_result = None
                else:
                    st.warning("请先训练模型")

        # ========== 独立显示优化结果（在按钮if块外面） ==========
        if st.session_state.ml_optimization_result is not None:
            optimization = st.session_state.ml_optimization_result

            if optimization.get('note'):
                st.info(f"💡 {optimization['note']}")

            st.subheader("🎯 推荐配方方案")

            for suggestion in optimization['suggestions']:
                # 创建一个更美观的展示
                with st.expander(f"⭐ 方案 {suggestion['ranking']} - 预测得分: {suggestion['predicted_score']} 分"):

                    # 使用列布局
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("### 📦 配方组成")

                        # A层
                        st.markdown(f"**A层（点火层）** - {suggestion['formula']['A层_点火层']['重量']}")
                        for comp, value in suggestion['formula']['A层_点火层']['成分'].items():
                            st.write(f"  • {comp}: {value}")

                        # B层
                        st.markdown(f"**B层（引燃层）** - {suggestion['formula']['B层_引燃层']['重量']}")
                        for comp, value in suggestion['formula']['B层_引燃层']['成分'].items():
                            st.write(f"  • {comp}: {value}")

                        # C层
                        st.markdown(f"**C层（主体层）** - {suggestion['formula']['C层_主体层']['重量']}")
                        for comp, value in suggestion['formula']['C层_主体层']['成分'].items():
                            st.write(f"  • {comp}: {value}")

                    with col2:
                        st.markdown("### ⚙️ 工艺参数")
                        for param, value in suggestion['process_params'].items():
                            st.write(f"• {param}: {value}")

                        st.markdown("### 📈 预期性能")
                        for metric, value in suggestion['expected_performance'].items():
                            if '异常概率' in metric:
                                prob_value = float(value.replace('%', ''))
                                if prob_value < 5:
                                    st.success(f"• {metric}: {value}")
                                elif prob_value < 10:
                                    st.warning(f"• {metric}: {value}")
                                else:
                                    st.error(f"• {metric}: {value}")
                            else:
                                st.write(f"• {metric}: {value}")

                    # 优化说明
                    if 'optimization_notes' in suggestion and suggestion['optimization_notes']:
                        st.markdown("### 💡 优化建议")
                        for note in suggestion['optimization_notes']:
                            if '偏低' in note or '偏高' in note:
                                st.warning(f"⚠️ {note}")
                            else:
                                st.info(f"ℹ️ {note}")

            # AS9100D提醒
            if optimization.get('AS9100D_reminder'):
                st.warning(f"📋 {optimization['AS9100D_reminder']}")

            # 下载配方报告
            report = st.session_state['ml_model'].generate_prediction_report(optimization)
            st.download_button(
                label="📥 下载配方优化报告",
                data=report,
                file_name=f"配方优化_{st.session_state.ml_target_score_used}分_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                key="download_formula_report"
            )
    
    with tab4:
        st.subheader("🔧 故障诊断系统")
        
        # 选择样品进行诊断
        selected_sample_diag = st.selectbox(
            "选择样品进行故障诊断",
            ranking_df['样品编号'].tolist(),
            key="fault_sample"
        )
        
        if st.button("🔍 开始诊断"):
            # 获取样品数据
            sample_row = ranking_df[ranking_df['样品编号'] == selected_sample_diag]
            
            if len(sample_row) == 0:
                st.error("未找到该样品数据")
            else:
                sample_data = sample_row.iloc[0]
                
                # 创建诊断系统
                diagnostics = FaultDiagnosticSystem()
                
                with st.spinner("正在进行故障诊断..."):
                    try:
                        diagnosis = diagnostics.diagnose(sample_data)
                        
                        # 显示诊断结果
                        st.success("✅ 诊断完成！")
                        
                        # 严重程度指示
                        severity_colors = {
                            'NORMAL': '🟢',
                            'LOW': '🟡',
                            'MEDIUM': '🟠',
                            'HIGH': '🔴',
                            'CRITICAL': '⚫'
                        }
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(
                                "严重程度",
                                f"{severity_colors[diagnosis['severity']]} {diagnosis['severity']}"
                            )
                        with col2:
                            st.metric("置信度", f"{diagnosis['confidence']:.1%}")
                        with col3:
                            st.metric("检测到的故障", len(diagnosis['detected_faults']))
                        
                        # 诊断总结
                        st.info(diagnosis['summary'])
                        
                        # 详细故障信息
                        if diagnosis['detected_faults']:
                            st.subheader("🔍 检测到的故障")
                            
                            for fault in diagnosis['detected_faults']:
                                with st.expander(f"{fault['fault_type']} (置信度: {fault['confidence']:.1%})"):
                                    st.write("**可能原因:**")
                                    for cause in fault['possible_causes']:
                                        st.write(f"• {cause}")
                                    
                                    st.write("**建议措施:**")
                                    for rec in fault['recommendations']:
                                        st.write(f"• {rec}")
                        
                        # AS9100D行动要求
                        as9100d = diagnosis.get('AS9100D_action', {})
                        if as9100d.get('action_required'):
                            st.warning(f"⚠️ AS9100D要求: {as9100d['description']}")
                        
                        # 下载诊断报告
                        report = diagnostics.generate_diagnostic_report(diagnosis)
                        st.download_button(
                            label="📥 下载诊断报告",
                            data=report,
                            file_name=f"{selected_sample_diag}_故障诊断.txt",
                            mime="text/plain"
                        )
                        
                    except Exception as e:
                        st.error(f"诊断失败: {e}")
    
    with tab5:
        st.subheader("🧪 DOE实验设计")
        
        # 设计类型选择
        design_type = st.selectbox(
            "选择实验设计类型",
            ["全因子设计", "部分因子设计", "响应面设计", "最优设计"],
            key="doe_type"
        )
        
        # 因子设置
        st.subheader("📝 设置实验因子")
        
        n_factors = st.number_input("因子数量", 2, 6, 3, key="n_factors_doe")
        
        factors = {}
        cols = st.columns(n_factors)
        
        default_factor_names = ['A层重量(g)', 'B层重量(g)', 'C层总重(g)', 
                               '压制压力(MPa)', '混料时间(min)', '氯酸钠含量(%)']
        
        default_lows = [5.0, 15.0, 340.0, 150.0, 10.0, 70.0]
        default_highs = [10.0, 25.0, 380.0, 250.0, 30.0, 85.0]
        
        for i, col in enumerate(cols[:n_factors]):
            with col:
                factor_name = st.text_input(
                    f"因子{i+1}名称",
                    default_factor_names[i] if i < len(default_factor_names) else f"因子{i+1}",
                    key=f"factor_name_{i}"
                )
                low = st.number_input(
                    f"低水平", 
                    value=default_lows[i] if i < len(default_lows) else 10.0,
                    key=f"low_level_{i}"
                )
                high = st.number_input(
                    f"高水平", 
                    value=default_highs[i] if i < len(default_highs) else 30.0,
                    key=f"high_level_{i}"
                )
                
                factors[factor_name] = {
                    'low': low,
                    'high': high,
                    'center': (low + high) / 2
                }
        
        # 如果是最优设计，添加实验次数选择
        if design_type == "最优设计":
            n_runs = st.slider("实验次数", 8, 50, 20, key="n_runs_doe")
        
        if st.button("🎲 生成实验设计", key="generate_doe"):
            designer = DOEDesigner()
            
            try:
                if design_type == "全因子设计":
                    design = designer.generate_factorial_design(factors, levels=2)
                elif design_type == "部分因子设计":
                    # 简化：使用2^(k-1)设计
                    design = designer.generate_factorial_design(factors, levels=2, fraction='half')
                elif design_type == "响应面设计":
                    design = designer.generate_response_surface_design(factors, design_type='ccd')
                elif design_type == "最优设计":
                    design = designer.generate_optimal_design(factors, n_runs if 'n_runs' in locals() else 20)
                
                st.success(f"✅ 生成了 {len(design)} 个实验")
                
                # 显示实验设计表
                st.dataframe(design, use_container_width=True)
                
                # 下载实验设计
                csv = design.to_csv(index=False)
                st.download_button(
                    label="📥 下载实验设计表",
                    data=csv,
                    file_name=f"DOE设计_{design_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_doe_csv"
                )
                
                # 生成报告
                report = designer.generate_doe_report(design)
                st.download_button(
                    label="📥 下载DOE报告",
                    data=report,
                    file_name=f"DOE报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    key="download_doe_report"
                )
                
            except Exception as e:
                st.error(f"生成设计失败: {e}")
    
    with tab6:
        st.subheader("💰 成本效益分析")
        
        # 成本分析类型
        analysis_type = st.radio(
            "选择分析类型",
            ["单产品成本", "批量成本对比", "成本优化"],
            key="cost_analysis_type"
        )
        
        if analysis_type == "单产品成本":
            # 输入配方
            st.subheader("📝 输入配方")
            
            col1, col2 = st.columns(2)
            
            formula = {}
            with col1:
                formula['氯酸钠'] = st.number_input("氯酸钠(g)", 0, 500, 300, key="naclo3_amount")
                formula['铁粉'] = st.number_input("铁粉(g)", 0, 100, 50, key="fe_amount")
                formula['玻璃纤维'] = st.number_input("玻璃纤维(g)", 0, 50, 20, key="glass_fiber_amount")
            
            with col2:
                formula['二氧化锰'] = st.number_input("二氧化锰(g)", 0, 50, 10, key="mno2_amount")
                batch_size = st.number_input("批次大小(个)", 1, 1000, 100, key="batch_size_cost")
                defect_rate = st.slider("缺陷率(%)", 0.0, 10.0, 2.0, key="defect_rate_cost") / 100
            
            if st.button("💵 计算成本", key="calculate_cost"):
                analyzer = CostAnalyzer()
                
                try:
                    # 计算总成本
                    cost_result = analyzer.calculate_total_cost(
                        formula, 
                        batch_size=batch_size,
                        defect_rate=defect_rate
                    )
                    
                    # 显示结果
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("单位总成本", f"¥{cost_result['unit_total_cost']}")
                    with col2:
                        st.metric("良品成本", f"¥{cost_result['good_product_cost']}")
                    with col3:
                        st.metric("材料成本", f"¥{cost_result['material_cost']['total_material_cost']}")
                    
                    # 成本结构饼图
                    st.subheader("📊 成本结构")
                    
                    fig = px.pie(
                        values=list(cost_result['cost_structure'].values()),
                        names=list(cost_result['cost_structure'].keys()),
                        title="成本构成分析"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 成本分解
                    with st.expander("查看详细成本分解"):
                        breakdown = analyzer.perform_cost_breakdown_analysis(formula)
                        
                        st.write("**帕累托分析（主要成本驱动因素）:**")
                        for item in breakdown['cost_drivers']:
                            st.write(f"• {item['material']}: ¥{item['cost']:.2f} ({item['percentage']:.1f}%)")
                    
                    # 下载报告
                    report = analyzer.generate_cost_report(cost_result)
                    st.download_button(
                        label="📥 下载成本报告",
                        data=report,
                        file_name=f"成本分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain",
                        key="download_cost_report"
                    )
                    
                except Exception as e:
                    st.error(f"成本计算失败: {e}")
        
        elif analysis_type == "批量成本对比":
            st.info("该功能正在开发中...")
        
        elif analysis_type == "成本优化":
            st.info("该功能正在开发中...")

# 页脚
st.markdown("---")
st.markdown("💡 **提示**: 使用左侧导航栏切换不同功能")
st.caption("氧烛分析系统 v1.4 | 作者: shiding")
