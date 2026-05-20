import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from pathlib import Path

# Set page config
st.set_page_config(page_title="渠道能力评估模型看板", layout="wide")

def resolve_default_excel():
    """Resolve default excel path robustly for cloud/local cwd differences."""
    base_dir = Path(__file__).resolve().parent
    preferred = base_dir / '渠道能力评估模型-CSA-2.0.xlsx'
    if preferred.exists():
        return preferred

    fallback_names = [
        '渠道能力评估模型-CSA.xlsx',
        '渠道能力评估模型-CSA -2.0.xlsx',
    ]
    for name in fallback_names:
        p = base_dir / name
        if p.exists():
            return p

    # Last fallback: try a fuzzy match in project root
    candidates = sorted(base_dir.glob('*CSA*.xlsx'))
    if candidates:
        return candidates[0]
    return preferred

@st.cache_data
def load_data(file_source):
    # Read the sheet, skipping the sub-header row for data but using it for names
    try:
        df_raw = pd.read_excel(file_source, sheet_name='评分详表', header=None)
    except Exception as e:
        st.error(f"加载文件失败，请确保Excel中包含‘评分详表’：{e}")
        return None, None
    
    # Extract headers
    # Row 0: Main headers
    # Row 1: Sub headers for Tech
    main_headers = df_raw.iloc[0].tolist()
    sub_headers = df_raw.iloc[1].tolist()
    
    # Clean data: skip the first two header rows
    df = df_raw.iloc[2:].reset_index(drop=True)
    
    # Define columns
    cols = [
        '区域', '分公司', '渠道名称', '渠道等级', '应用专员', '能力评级', '原始评分合计',
        '性能验证能力', '无忧切换能力', '结果问题解决能力', '风险管理能力', 
        'IQC/EQA管理能力', '瑞印课堂-系列课能力', '产品价值优势传递能力', '学术支持&文章合作能力',
        '工作态度与责任心', '学习成长能力', '沟通协助能力', '执行力与结果产出'
    ]
    df.columns = cols
    
    # Convert numeric columns
    numeric_cols = cols[6:]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Recalculate total score based on the logic:
    # Tech (40%): Avg of 8 sub-dims * 4
    # Attitude (10%): Score * 1
    # Learning (20%): Score * 2
    # Comm (15%): Score * 1.5
    # Execution (15%): Score * 1.5
    tech_cols = cols[7:15]
    df['专业技术能力'] = df[tech_cols].mean(axis=1)
    df['评分合计'] = (
        df['专业技术能力'] * 4 + 
        df['工作态度与责任心'] * 1 + 
        df['学习成长能力'] * 2 + 
        df['沟通协助能力'] * 1.5 + 
        df['执行力与结果产出'] * 1.5
    )
    
    return df, tech_cols

def main():
    # Custom CSS for better looking cards and compact layout
    st.markdown("""
    <style>
    /* Reduce top padding of the main container */
    .main .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    .compact-title {
        font-size: 1.6rem !important;
        font-weight: 700;
        margin-bottom: 0.8rem !important;
        padding-top: 0px !important;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 6px;
        padding: 5px 10px;
        border-left: 3px solid #008080;
        box-shadow: 1px 1px 2px rgba(0,0,0,0.05);
        margin-bottom: 5px;
        text-align: center;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #6c757d;
        margin-bottom: 0px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
    }
    .metric-value {
        font-size: 1.2rem;
        font-weight: bold;
        color: #212529;
    }
    .total-score-card {
        background: linear-gradient(90deg, #008080 0%, #004d4d 100%);
        color: white;
        border-radius: 6px;
        padding: 5px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 10px;
    }
    .total-score-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .total-score-value {
        font-size: 1.8rem;
        font-weight: bold;
        margin: 0 15px;
    }
    .total-score-delta {
        font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="compact-title">📊 渠道能力评估模型看板 (CSA)</div>', unsafe_allow_html=True)
    
    # --- Authentication System ---
    st.sidebar.header("🔐 访问权限控制")
    # Simple passcode-to-region mapping (You can modify this)
    # Admin passcode: 'admin123' -> sees all
    # Region passcodes: 'north123' -> '北部区', etc.
    AUTH_DATA = {
        'admin123': 'Admin',
        'nw123': '西北区',
        'ne123': '东北区',
        'sw123': '西南区',
        'se123': '东南区',
        'nc123': '华北区',
        'ec123': '华东区',
        'cc123': '华中区',
        'sc123': '华南区'
    }
    
    passcode = st.sidebar.text_input("输入通行证查看对应区域数据", type="password")
    
    user_role = AUTH_DATA.get(passcode)
    
    if not user_role:
        st.info("👈 请在左侧侧边栏输入正确的【通行证】以解锁数据查看权限。")
        st.stop()
    
    st.sidebar.success(f"当前身份: {user_role}")
    
    # Sidebar - File Upload
    st.sidebar.divider()
    st.sidebar.header("📁 数据源选择")
    uploaded_file = st.sidebar.file_uploader("上传评估数据 (Excel)", type=["xlsx"])
    
    # Use default file if no file is uploaded
    file_source = uploaded_file if uploaded_file is not None else str(resolve_default_excel())
    
    df, tech_cols = load_data(file_source)
    
    if df is None:
        st.warning("⚠️ 请上传正确的 Excel 文件以继续。")
        return
    
    # Sidebar - Filters
    st.sidebar.divider()
    st.sidebar.header("🔍 筛选器")
    
    # Permission Logic: Lock area if not admin
    all_areas = df['区域'].unique()
    if user_role == 'Admin':
        selected_area = st.sidebar.multiselect("选择区域", options=all_areas, default=all_areas)
    else:
        # User is locked to their region
        if user_role in all_areas:
            selected_area = [user_role]
            st.sidebar.info(f"📍 已锁定区域: {user_role}")
        else:
            st.error(f"❌ 通行证对应的区域 '{user_role}' 在当前数据中未找到。")
            st.stop()
    
    # Branch selection dependent on area
    branch_options = df[df['区域'].isin(selected_area)]['分公司'].unique()
    selected_branch = st.sidebar.multiselect("选择分公司", options=branch_options, default=branch_options)
    
    filtered_df = df[df['区域'].isin(selected_area) & df['分公司'].isin(selected_branch)]
    
    selected_person = st.sidebar.selectbox("选择人员查看详细报告", options=filtered_df['应用专员'].unique())
    
    st.sidebar.subheader("雷达图对比选项")
    show_area_avg = st.sidebar.checkbox("对比区域平均水平", value=False)
    show_branch_avg = st.sidebar.checkbox("对比分公司平均水平", value=False)
    
    person_data = filtered_df[filtered_df['应用专员'] == selected_person].iloc[0]
    categories = ['专业技术能力', '工作态度与责任心', '学习成长能力', '沟通协助能力', '执行力与结果产出']

    # --- Compact Score Section at Top ---
    # Total Score as a thin bar
    delta_val = person_data['评分合计'] - df['评分合计'].mean()
    delta_str = f"↑ {delta_val:.1f}" if delta_val >= 0 else f"↓ {abs(delta_val):.1f}"
    delta_color = "lightgreen" if delta_val >= 0 else "#ff4b4b"
    
    st.markdown(f"""
    <div class="total-score-card">
        <div class="total-score-label">评分合计 (总分 100)</div>
        <div class="total-score-value">{person_data['评分合计']:.1f}</div>
        <div class="total-score-delta" style="color: {delta_color}; font-weight: bold;">
            {delta_str} (vs 团队平均)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Dimension scores as very compact cards in one row
    score_cols = st.columns(len(categories))
    for i, cat in enumerate(categories):
        with score_cols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label" title="{cat}">{cat}</div>
                <div class="metric-value">{person_data[cat]:.1f}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # st.markdown("<br>", unsafe_allow_html=True) # Reduced space

    # Layout for charts
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader(f"👤 个人能力画像: {selected_person}")
        
        # Prepare data for Radar Chart (5 main dimensions)
        values = [person_data[cat] for cat in categories]
        
        fig = go.Figure()
        
        # Selected person trace
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=selected_person,
            line_color='teal'
        ))
        
        # Area average trace (optional)
        if show_area_avg:
            area_avg_df = df[df['区域'].isin(selected_area)]
            area_avg_values = [area_avg_df[cat].mean() for cat in categories]
            fig.add_trace(go.Scatterpolar(
                r=area_avg_values,
                theta=categories,
                fill='none',
                name='区域平均',
                line=dict(color='orange', dash='dash')
            ))
            
        # Branch average trace (optional)
        if show_branch_avg:
            branch_avg_df = df[df['分公司'].isin(selected_branch)]
            branch_avg_values = [branch_avg_df[cat].mean() for cat in categories]
            fig.add_trace(go.Scatterpolar(
                r=branch_avg_values,
                theta=categories,
                fill='none',
                name='分公司平均',
                line=dict(color='purple', dash='dot')
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 10])
            ),
            showlegend=show_area_avg or show_branch_avg,
            legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5),
            height=450
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("🛠 专业技术能力细分维度拆解")
        tech_labels = [col.replace('能力', '') for col in tech_cols]
        tech_values = [person_data[col] for col in tech_cols]
        
        fig_tech = go.Figure()
        
        # Individual scores as horizontal bars
        fig_tech.add_trace(go.Bar(
            y=tech_labels,
            x=tech_values,
            orientation='h',
            name=selected_person,
            marker=dict(
                color=tech_values,
                colorscale='tealgrn', # Use valid colorscale name
                showscale=False
            ),
            text=tech_values,
            textposition='auto',
            texttemplate='%{x:.1f}'
        ))
        
        # Area average as markers
        if show_area_avg:
            area_tech_avg = [df[df['区域'].isin(selected_area)][col].mean() for col in tech_cols]
            fig_tech.add_trace(go.Scatter(
                y=tech_labels,
                x=area_tech_avg,
                mode='markers',
                name='区域平均',
                marker=dict(color='orange', size=12, symbol='line-ns-open', line_width=3)
            ))
            
        # Branch average as markers
        if show_branch_avg:
            branch_tech_avg = [df[df['分公司'].isin(selected_branch)][col].mean() for col in tech_cols]
            fig_tech.add_trace(go.Scatter(
                y=tech_labels,
                x=branch_tech_avg,
                mode='markers',
                name='分公司平均',
                marker=dict(color='purple', size=12, symbol='line-ns-open', line_width=3)
            ))
            
        fig_tech.update_layout(
            xaxis=dict(title='分数', range=[0, 10.5], dtick=2),
            yaxis=dict(autorange="reversed"), # High scores at top
            showlegend=show_area_avg or show_branch_avg,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=450,
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig_tech, use_container_width=True)

    st.divider()
    
    # Team Health Section
    st.header("🌐 团队整体健康度")
    
    t_col1, t_col2 = st.columns([1, 2])
    
    with t_col1:
        avg_total = filtered_df['评分合计'].mean()
        st.markdown(f"""
        <div class="total-score-card" style="margin-bottom: 20px;">
            <div style="font-size: 1.2rem; opacity: 0.9;">团队平均分</div>
            <div class="total-score-value">{avg_total:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Capability Level Distribution
        level_counts = filtered_df['能力评级'].value_counts().sort_index()
        fig_level = px.pie(names=level_counts.index, values=level_counts.values, title="能力评级分布", hole=0.4)
        fig_level.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_level, use_container_width=True)
    
    with t_col2:
        # Top Performers
        st.subheader("🏆 顶尖人才 (Top 5)")
        top_5 = filtered_df.nlargest(5, '评分合计')[['应用专员', '分公司', '渠道名称', '评分合计', '能力评级']]
        st.table(top_5)
    
    # Team Dimension Average
    st.subheader("📈 团队各维度平均表现")
    avg_dims = filtered_df[categories].mean()
    fig_avg = px.line_polar(r=avg_dims.values, theta=avg_dims.index, line_close=True)
    fig_avg.update_traces(fill='toself', line_color='orange')
    fig_avg.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 10])), height=400)
    st.plotly_chart(fig_avg, use_container_width=True)

    # --- New Section: Channel Capability Analysis ---
    st.divider()
    st.header("🏢 渠道商能力对标")
    
    # Group by Channel Name
    channel_stats = filtered_df.groupby('渠道名称').agg({
        '评分合计': ['mean', 'count', 'max', 'min'],
        '应用专员': lambda x: ', '.join(x)
    }).reset_index()
    channel_stats.columns = ['渠道名称', '平均分', '总人数', '最高分', '最低分', '人员名单']
    channel_stats = channel_stats.sort_values('平均分', ascending=False)

    # Readability controls for crowded channel charts
    st.caption("图表优化：当渠道数量较多时，可通过下方参数减少重叠、聚焦关键渠道。")
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 1, 1])
    with ctrl_col1:
        min_headcount = st.number_input("最少专员人数门槛", min_value=1, max_value=50, value=2, step=1)
    with ctrl_col2:
        top_n = st.slider("展示 Top N 渠道（按平均分）", min_value=5, max_value=min(60, max(5, len(channel_stats))), value=min(20, len(channel_stats)))
    with ctrl_col3:
        only_top_for_scatter = st.checkbox("分布图仅显示 Top N", value=False)

    filtered_channel_stats = channel_stats[channel_stats['总人数'] >= min_headcount].copy()
    if filtered_channel_stats.empty:
        st.warning("当前门槛下没有可展示的渠道，请降低“最少专员人数门槛”。")
        return

    channel_stats_top = filtered_channel_stats.head(top_n).copy()

    c_col1, c_col2 = st.columns([2, 1])

    with c_col1:
        st.subheader("渠道商平均分对标")
        # Horizontal bar chart for channel comparison (top N to avoid overcrowding)
        fig_channel = px.bar(
            channel_stats_top.sort_values('平均分', ascending=True),
            x='平均分',
            y='渠道名称',
            orientation='h',
            color='平均分',
            color_continuous_scale='tealgrn',
            text='平均分',
            hover_data=['总人数', '最高分', '最低分', '人员名单']
        )
        fig_channel.update_traces(texttemplate='%{x:.1f}', textposition='outside')
        fig_channel.update_layout(
            yaxis={'categoryorder':'total ascending'},
            height=max(420, len(channel_stats_top) * 26), # Dynamic height with cap via top_n
            xaxis_range=[0, 105],
            margin=dict(l=10, r=10, t=40, b=20)
        )
        st.plotly_chart(fig_channel, use_container_width=True)

    with c_col2:
        st.subheader("渠道能力分布概览")
        scatter_source = channel_stats_top if only_top_for_scatter else filtered_channel_stats
        scatter_source = scatter_source.copy()
        # Slight jitter on x to reduce exact overlap when headcount is same
        scatter_source['总人数抖动'] = scatter_source['总人数'] + np.random.uniform(-0.12, 0.12, len(scatter_source))

        # Bubble chart: x=headcount, y=avg score
        fig_scatter = px.scatter(
            scatter_source,
            x='总人数抖动',
            y='平均分',
            size='总人数',
            color='平均分',
            hover_name='渠道名称',
            color_continuous_scale='tealgrn',
            labels={'总人数抖动': '专员人数', '平均分': '渠道平均分'},
            hover_data={'总人数': True, '最高分': ':.1f', '最低分': ':.1f'}
        )
        fig_scatter.update_traces(
            marker=dict(
                sizemode='area',
                sizeref=max(0.2, 2.0 * scatter_source['总人数'].max() / (42.0 ** 2)),
                sizemin=8,
                line=dict(width=0.8, color='white'),
                opacity=0.75
            )
        )
        fig_scatter.update_layout(
            height=420,
            xaxis=dict(title='专员人数', dtick=1),
            yaxis=dict(title='渠道平均分', range=[0, 100]),
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        
        st.info("💡 气泡图已恢复：横轴为专员人数，纵轴为渠道平均分；同人数渠道已做轻微错位，避免完全重叠。")

    # Channel Detail Selection
    selected_channel = st.selectbox("选择渠道商查看内部人员明细", options=filtered_channel_stats['渠道名称'].unique())
    if selected_channel:
        channel_detail = filtered_df[filtered_df['渠道名称'] == selected_channel].sort_values('评分合计', ascending=False)
        st.write(f"🔍 **{selected_channel}** 共有 {len(channel_detail)} 名专员：")
        
        # Display as a pretty table
        st.dataframe(
            channel_detail[['应用专员', '评分合计', '能力评级', '分公司'] + categories],
            use_container_width=True
        )

    # Full Data View
    if st.checkbox("查看完整评分数据"):
        st.dataframe(filtered_df)

if __name__ == "__main__":
    main()
