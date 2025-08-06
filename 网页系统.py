#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
氧烛分析Web系统 - 修复配方对比功能
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

# 尝试导入配方解析模块 - 不使用缓存的导入
try:
    from modules.formula_parser import FormulaParser
    FORMULA_MODULE_LOADED = True
except:
    FORMULA_MODULE_LOADED = False

# 页面配置
st.set_page_config(
    page_title="氧烛分析系统",
    page_icon="🔥",
    layout="wide"
)

# 标题
st.title("🔥 氧烛产品分析系统")
st.markdown("---")

# 侧边栏
st.sidebar.header("📊 功能导航")
page = st.sidebar.radio(
    "选择功能",
    ["主页", "数据总览", "排名分析", "对比分析", "最佳配方"]
)

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

# 初始化配方解析器 - 修改为不使用缓存或使用不同的缓存策略
@st.cache_resource
def get_formula_parser_cached():
    """获取配方解析器实例（缓存版）"""
    if FORMULA_MODULE_LOADED:
        try:
            parser = FormulaParser("./data/配方表.xlsx")
            if parser and parser.product_formulas:
                return parser
        except:
            pass
    return None

# 不使用缓存的版本，用于调试
def get_formula_parser():
    """获取配方解析器实例（非缓存版）"""
    if FORMULA_MODULE_LOADED:
        try:
            parser = FormulaParser("./data/配方表.xlsx")
            if parser and parser.product_formulas:
                return parser
        except Exception as e:
            st.error(f"配方解析器初始化失败: {e}")
    return None

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

# 对比分析（修复配方对比）
elif page == "对比分析":
    st.header("📊 对比分析")
    
    # 选择要对比的样品
    selected = st.multiselect(
        "选择要对比的样品（最多6个）",
        options=ranking_df['样品编号'].tolist(),
        default=ranking_df.head(3)['样品编号'].tolist()
    )
    
    if len(selected) > 6:
        st.warning("最多选择6个样品")
        selected = selected[:6]
    
    if selected:
        # 筛选数据
        compare_df = ranking_df[ranking_df['样品编号'].isin(selected)]
        
        # 创建四个标签页
        tab1, tab2, tab3, tab4 = st.tabs(["📈 流量曲线对比", "📊 燃烧深度分析", "🧪 配方对比", "📋 详细数据"])
        
        with tab1:
            st.subheader("流量曲线对比")
            
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
            colors_list = ['blue', 'green', 'orange', 'purple', 'brown', 'pink']
            
            # 为每个选中的样品添加流量曲线
            for idx, sample_id in enumerate(selected):
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
                title="流量曲线对比图",
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
            st.info("""
            💡 **使用说明**：
            - 拖动底部滑块可以放大查看特定时间段
            - 鼠标悬停查看具体数值
            - 点击图例可以显示/隐藏对应曲线
            """)
        
        with tab2:
            st.subheader("燃烧深度分析")
            
            # 创建燃烧深度对比图
            fig2 = make_subplots(
                rows=2, cols=1,
                row_heights=[0.7, 0.3],
                subplot_titles=("燃烧深度随时间变化", "燃烧速率对比"),
                vertical_spacing=0.15
            )
            
            # 存储每个样品的燃烧数据
            burn_data = {}
            colors_list = ['blue', 'green', 'orange', 'purple', 'brown', 'pink']
            
            for idx, sample_id in enumerate(selected):
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
            st.subheader("🧪 配方对比分析")
            
            if FORMULA_MODULE_LOADED:
                # 获取配方解析器 - 使用非缓存版本
                parser = get_formula_parser()
                
                if parser and parser.product_formulas:
                    # 显示调试信息
                    with st.expander("调试信息"):
                        st.write(f"已加载 {len(parser.product_formulas)} 个产品配方")
                        st.write(f"选中的产品: {selected}")
                        st.write(f"可用的产品ID示例: {list(parser.product_formulas.keys())[:10]}")
                    
                    # 进行配方对比
                    comparison = parser.compare_formulas(selected)
                    
                    if 'message' in comparison:
                        st.error(comparison['message'])
                    elif comparison and 'comparisons' in comparison:
                        # 显示基准产品
                        st.info(f"📌 **基准产品**: {comparison['base_product']}")
                        st.write(f"**基准配方**: {comparison['base_formula']}")
                        
                        st.markdown("---")
                        
                        # 创建对比表
                        for product_id, diff in comparison['comparisons'].items():
                            if 'status' in diff:
                                st.warning(f"{product_id}: {diff['status']}")
                                continue
                            
                            with st.expander(f"📊 {product_id} vs {comparison['base_product']}"):
                                st.write(f"**配方**: {diff.get('formula_string', '')}")
                                
                                # 显示配方差异
                                if diff.get('differences'):
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
                                
                                # 显示成分变化
                                if diff.get('component_details'):
                                    st.write("**成分具体变化:**")
                                    for layer, changes in diff['component_details'].items():
                                        st.write(f"*{layer}:*")
                                        for change in changes:
                                            if change['type'] == '新增':
                                                st.write(f"  - ➕ {change['description']}")
                                            elif change['type'] == '删除':
                                                st.write(f"  - ➖ {change['description']}")
                                            else:
                                                st.write(f"  - 🔄 {change['description']}")
                                
                                if not diff.get('differences') and not diff.get('component_details'):
                                    st.success("✅ 配方完全相同")
                    else:
                        st.warning("未找到配方数据")
                else:
                    st.error("配方解析器初始化失败或未加载到产品配方")
                    st.write(f"模块加载状态: {FORMULA_MODULE_LOADED}")
                    if parser:
                        st.write(f"产品配方数量: {len(parser.product_formulas) if parser.product_formulas else 0}")
            else:
                st.warning("""
                ⚠️ 配方对比模块未加载。请确保：
                1. 配方表.xlsx 文件在 data 目录
                2. formula_parser.py 在 modules 目录
                3. 配方表包含"总表"、"A层"、"B层"、"C层"sheet
                """)
        
        with tab4:
            st.subheader("📋 详细对比")
            st.dataframe(compare_df, use_container_width=True)

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

# 页脚
st.markdown("---")
st.markdown("💡 **提示**: 使用左侧导航栏切换不同功能")
st.caption("氧烛分析系统 v1.0 | 作者: shiding")
