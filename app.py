import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

from data_processor import (
    load_csv, preprocess_data, apply_filters, minutes_to_time_display,
    normalize_columns, check_data_quality
)
from analyzer import (
    compute_basic_stats, compute_stability_score, detect_patterns,
    compute_correlations, compare_to_norms, compute_group_stats,
    age_based_sleep_norms
)
from visualizer import (
    plot_sleep_trend, plot_nightwaking_heatmap, plot_naps_distribution,
    plot_stability_gauge, plot_stability_radar, plot_bedtime_vs_wakings,
    plot_milk_analysis, plot_age_comparison, plot_weekly_pattern
)
from advisor import generate_sleep_advice, export_report_to_excel
from data_quality import analyze_data_quality, get_filtered_df


st.set_page_config(
    page_title='宝宝睡眠节律与夜醒诱因分析台',
    page_icon='🌙',
    layout='wide',
    initial_sidebar_state='expanded'
)

st.markdown("""
<style>
.stMetric {
    background: #f8fafc;
    padding: 1rem;
    border-radius: 12px;
    border-left: 4px solid #6366F1;
}
.stMetric > div {
    background: transparent !important;
}
div[data-testid="stMetricValue"] {
    color: #1e293b;
    font-weight: 600;
}
div[data-testid="stMetricLabel"] {
    color: #64748b;
    font-size: 0.85rem;
}
.pattern-card {
    padding: 1rem 1.2rem;
    border-radius: 10px;
    margin: 0.5rem 0;
    border-left: 4px solid;
}
.pattern-warning {
    background: #FEF2F2;
    border-color: #EF4444;
}
.pattern-info {
    background: #EFF6FF;
    border-color: #3B82F6;
}
.pattern-success {
    background: #ECFDF5;
    border-color: #10B981;
}
.advice-card {
    background: #F5F3FF;
    padding: 1.2rem;
    border-radius: 12px;
    border: 1px solid #DDD6FE;
    margin: 0.5rem 0;
}
.priority-high {
    background: #FEF2F2;
    border-left: 4px solid #DC2626;
    padding: 0.8rem 1rem;
    border-radius: 8px;
    margin: 0.4rem 0;
}
.priority-medium {
    background: #FFFBEB;
    border-left: 4px solid #F59E0B;
    padding: 0.8rem 1rem;
    border-radius: 8px;
    margin: 0.4rem 0;
}
.priority-low {
    background: #F0FDF4;
    border-left: 4px solid #22C55E;
    padding: 0.8rem 1rem;
    border-radius: 8px;
    margin: 0.4rem 0;
}
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #374151;
    padding: 0.5rem 0;
    margin-bottom: 0.8rem;
    border-bottom: 2px solid #E5E7EB;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title('🌙 控制面板')
    st.markdown('---')
    
    st.subheader('📁 数据上传')
    uploaded_file = st.file_uploader(
        '上传宝宝作息记录 CSV',
        type=['csv'],
        help='必需列：日期、月龄、入睡时间、起床时间、夜醒次数；可选列：白天小睡次数、小睡总时长、奶量、喂养方式、是否长牙、天气、夜醒时段'
    )
    
    use_sample = st.checkbox('使用示例数据（测试用）', value=False)


def load_data():
    df = None
    msg = None
    if use_sample:
        try:
            import generate_sample_data
            csv_content = generate_sample_data.generate_csv()
            from io import StringIO
            df = pd.read_csv(StringIO(csv_content))
            df = normalize_columns(df)
            msg = None
        except Exception as e:
            msg = f'生成示例数据失败: {e}'
    elif uploaded_file is not None:
        df, msg = load_csv(uploaded_file)
    return df, msg


df_raw, load_msg = load_data()

processed_df = None
data_quality = None
data_quality_result = None

if df_raw is not None:
    with st.spinner('正在处理数据...'):
        processed_df = preprocess_data(df_raw)
        st.session_state.processed_df = processed_df
        
        data_quality = check_data_quality(processed_df)
        st.session_state.data_quality = data_quality
        
        data_quality_result = analyze_data_quality(processed_df)
        st.session_state.data_quality_result = data_quality_result

filter_age = '全部'
filter_feeding = '全部'
filter_teething = '全部'
filter_weather = '全部'
date_range = None
exclude_anomalies = True
analysis_mode = '总览仪表盘'

with st.sidebar:
    st.markdown('---')
    st.subheader('🔍 筛选条件')
    
    if processed_df is not None:
        df = processed_df
        
        age_options = ['全部'] + sorted(df['age_group'].unique().tolist())
        filter_age = st.selectbox('月龄阶段', age_options, index=0)
        
        feeding_options = ['全部'] + sorted(df['feeding_type'].unique().tolist())
        filter_feeding = st.selectbox('喂养方式', feeding_options, index=0)
        
        teething_options = ['全部'] + sorted(df['teething'].unique().tolist())
        filter_teething = st.selectbox('是否长牙', teething_options, index=0)
        
        weather_options = ['全部'] + sorted(df['weather'].unique().tolist())
        filter_weather = st.selectbox('天气', weather_options, index=0)
        
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        if min_date != max_date:
            date_range = st.date_input(
                '日期范围',
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
    
    excluded_count = 0
    if data_quality_result is not None:
        excluded_count = data_quality_result.get('excluded_records', 0)
    
    st.markdown('---')
    st.subheader('🛡️ 数据质量')
    if processed_df is not None:
        exclude_anomalies = st.toggle(
            '排除影响睡眠时长的异常记录',
            value=True,
            help='默认排除入睡/起床时间缺失、格式错误或睡眠时长异常的记录，关闭后可对比包含异常的统计结果'
        )
        if excluded_count > 0:
            st.caption(f"共 {excluded_count} 条严重异常记录会被排除")
        else:
            st.info('✅ 当前未检测到影响睡眠时长的严重异常')
    
    st.markdown('---')
    st.subheader('📊 分析维度')
    analysis_mode = st.radio(
        '选择分析视角',
        ['总览仪表盘', '深度模式分析', '分组对比分析', '睡眠节律建议'],
        index=0
    )
    
    st.markdown('---')
    st.caption('💡 建议连续记录7天以上数据以获得更准确的分析')

st.title('🌙 宝宝睡眠节律与夜醒诱因分析台')
st.caption('基于 CSV 作息记录，自动分析睡眠模式、识别夜醒诱因、提供个性化节律建议')

if df_raw is None:
    if load_msg and '请上传' not in load_msg:
        st.error(load_msg)
    
    st.info('👆 请在左侧面板上传 CSV 文件，或勾选「使用示例数据」开始体验分析功能')
    
    with st.expander('📋 CSV 格式说明', expanded=True):
        st.markdown("""
        **必需列（缺一不可）：**
        | 列名 | 示例 | 说明 |
        |------|------|------|
        | 日期 | 2025-06-01 | YYYY-MM-DD 格式 |
        | 月龄 | 7.5 | 月为单位，支持小数 |
        | 入睡时间 | 21:30 或 21.5 | HH:MM 或小数小时 |
        | 起床时间 | 07:00 或 7 | HH:MM 或小数小时 |
        | 夜醒次数 | 2 | 整数 |
        
        **重要可选列（强烈建议补充）：**
        | 列名 | 示例 | 说明 |
        |------|------|------|
        | 白天小睡次数 | 3 | 整数 |
        | 白天小睡总时长(分钟) | 180 | 分钟数 |
        | 奶量(ml) | 750 | 当日总奶量 |
        | 喂养方式 | 母乳/配方奶/混合 | 分类数据 |
        | 是否长牙 | 是/否 | 长牙期标记 |
        | 天气 | 晴/雨/热/冷 | 占位变量 |
        | 夜醒时段 | 2:30,5:15 | 逗号分隔的夜醒时间点 |
        | last_nap_end | 16:00 | 白天最后一觉结束时间 |
        """)
    st.stop()

quality_filtered_df = get_filtered_df(processed_df, data_quality_result, exclude_anomalies=exclude_anomalies)

filtered_df = apply_filters(
    quality_filtered_df,
    age_group=filter_age,
    feeding_type=filter_feeding,
    teething=filter_teething,
    weather=filter_weather,
    date_range=date_range
)

if len(filtered_df) == 0:
    st.warning('筛选条件下无数据，请调整筛选设置')
    st.stop()

stats = compute_basic_stats(filtered_df)
stability = compute_stability_score(filtered_df)
patterns = detect_patterns(filtered_df)
advice = generate_sleep_advice(filtered_df, patterns, stability, stats)

st.success(f'✅ 数据加载完成：{stats["days_recorded"]} 天记录，{stats["date_range"][0]} ~ {stats["date_range"][1]}')

with st.container():
    st.markdown("""
    <style>
    .quality-panel {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #bae6fd;
    }
    .quality-score-circle {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.8rem;
        font-weight: 700;
        color: white;
        flex-shrink: 0;
    }
    .quality-item {
        background: white;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        margin: 0.3rem 0;
        border-left: 3px solid;
    }
    .quality-critical { border-color: #ef4444; }
    .quality-warning { border-color: #f59e0b; }
    .quality-info { border-color: #3b82f6; }
    .quality-fixed { border-color: #10b981; }
    </style>
    """, unsafe_allow_html=True)
    
    qr = data_quality_result
    score = qr.get('score', 0)
    level = qr.get('level', '')
    total = qr.get('total_records', 0)
    valid = qr.get('valid_records', 0)
    excluded = qr.get('excluded_records', 0)
    fixable = qr.get('fixable_count', 0)
    
    if score >= 90:
        score_color = '#10b981'
    elif score >= 75:
        score_color = '#3b82f6'
    elif score >= 60:
        score_color = '#f59e0b'
    elif score >= 40:
        score_color = '#f97316'
    else:
        score_color = '#ef4444'
    
    st.markdown(f"""
    <div class="quality-panel">
        <div style="display:flex;align-items:center;gap:1.5rem;">
            <div class="quality-score-circle" style="background:{score_color}">
                {score}
            </div>
            <div style="flex:1;">
                <div style="font-size:1.2rem;font-weight:600;color:#0f172a;margin-bottom:0.3rem">
                    数据质量评分：{level}
                </div>
                <div style="color:#475569;font-size:0.9rem;">
                    共 {total} 条记录，有效 {valid} 条，排除 {excluded} 条（影响睡眠时长），自动修正 {fixable} 条
                </div>
                <div style="color:#64748b;font-size:0.85rem;margin-top:0.3rem">
                    {"⚠️ 当前已排除异常记录，统计结果基于有效数据" if exclude_anomalies else "📊 当前包含所有记录（含异常），统计结果可能失真"}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    anomaly_records = qr.get('anomaly_records', [])
    if anomaly_records:
        with st.expander(f'📋 异常记录详情（{len(anomaly_records)} 条）', expanded=excluded > 0):
            critical_recs = [r for r in anomaly_records if r['severity'] == 'critical']
            warning_recs = [r for r in anomaly_records if r['severity'] == 'warning']
            fix_recs = [r for r in anomaly_records if r['is_fixable']]
            
            if critical_recs:
                st.markdown(f"**🔴 严重问题（{len(critical_recs)} 条，默认排除）**")
                for rec in critical_recs[:5]:
                    issues_str = '；'.join([i['message'] for i in rec['issues'] if i['severity'] == 'critical'])
                    affected = '、'.join(rec['affected_fields']) if rec['affected_fields'] else '未知'
                    st.markdown(f"""
                    <div class="quality-item quality-critical">
                        <div style="font-weight:600;color:#991b1b">{rec['date']}</div>
                        <div style="color:#4b5563;font-size:0.9rem;margin-top:2px">{issues_str}</div>
                        <div style="color:#6b7280;font-size:0.8rem;margin-top:2px">影响字段：{affected}</div>
                    </div>
                    """, unsafe_allow_html=True)
                if len(critical_recs) > 5:
                    st.caption(f'... 还有 {len(critical_recs) - 5} 条严重问题记录')
            
            if warning_recs:
                st.markdown(f"**🟡 警告级问题（{len(warning_recs)} 条）**")
                for rec in warning_recs[:5]:
                    issues_str = '；'.join([i['message'] for i in rec['issues'] if i['severity'] == 'warning'])
                    st.markdown(f"""
                    <div class="quality-item quality-warning">
                        <div style="font-weight:600;color:#92400e">{rec['date']}</div>
                        <div style="color:#4b5563;font-size:0.9rem;margin-top:2px">{issues_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                if len(warning_recs) > 5:
                    st.caption(f'... 还有 {len(warning_recs) - 5} 条警告级记录')
            
            if fix_recs:
                st.markdown(f"**✅ 已自动修正（{len(fix_recs)} 条）**")
                for rec in fix_recs[:5]:
                    fixes_str = '；'.join([f['message'] for f in rec['fixes']])
                    st.markdown(f"""
                    <div class="quality-item quality-fixed">
                        <div style="font-weight:600;color:#065f46">{rec['date']}</div>
                        <div style="color:#4b5563;font-size:0.9rem;margin-top:2px">{fixes_str}</div>
                    </div>
                    """, unsafe_allow_html=True)
                if len(fix_recs) > 5:
                    st.caption(f'... 还有 {len(fix_recs) - 5} 条已修正记录')
            
            st.markdown('---')
            st.caption('💡 可在左侧「数据质量」面板切换「排除/纳入异常记录」对比分析结果差异')

if data_quality['warnings']:
    with st.expander('⚡ 补充提示（点击查看）', expanded=False):
        for w in data_quality['warnings']:
            st.warning(w)

if data_quality['info']:
    with st.expander('ℹ️ 数据说明（点击查看）', expanded=False):
        for info in data_quality['info']:
            st.info(info)


if analysis_mode == '总览仪表盘':
    st.markdown('### 📊 核心指标一览')
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('总睡眠时长', f'{stats["avg_total_sleep_hours"]} h/天', 
                  help='夜间+白天小睡')
    with col2:
        st.metric('夜间睡眠', f'{stats["avg_night_sleep_hours"]} h',
                  help='入睡到起床的总时长')
    with col3:
        st.metric('平均夜醒', f'{stats["avg_nightwakings"]} 次/夜',
                  help=f'{stats["night_waking_days_pct"]}% 的天有夜醒')
    with col4:
        st.metric('作息稳定度', f'{stability["overall"]} 分',
                  delta=stability.get('level', ''),
                  delta_color='off' if stability['overall'] < 60 else 'normal')
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric('平均入睡时间', stats["avg_bedtime"])
    with col6:
        st.metric('平均起床时间', stats["avg_wakeup"])
    with col7:
        st.metric('白天小睡', f'{stats["avg_naps_count"]} 次 / {stats["avg_nap_hours"]}h')
    with col8:
        milk = f'{stats["avg_milk_ml"]:.0f} ml' if stats['avg_milk_ml'] else '未记录'
        st.metric('日均奶量', milk)
    
    st.markdown('---')
    
    tab1, tab2, tab3 = st.tabs(['📈 睡眠趋势与夜醒', '🔥 夜醒热力图 & 稳定度', '😴 小睡分析 & 入睡关系'])
    
    with tab1:
        st.plotly_chart(plot_sleep_trend(filtered_df), use_container_width=True)
    
    with tab2:
        c1, c2 = st.columns([1.5, 1])
        with c1:
            st.plotly_chart(plot_nightwaking_heatmap(filtered_df), use_container_width=True)
        with c2:
            st.plotly_chart(plot_stability_gauge(stability), use_container_width=True)
            st.info(f'💡 {stability.get("details", "")}')
            st.plotly_chart(plot_stability_radar(stability), use_container_width=True)
    
    with tab3:
        st.plotly_chart(plot_naps_distribution(filtered_df), use_container_width=True)
        st.plotly_chart(plot_bedtime_vs_wakings(filtered_df), use_container_width=True)
    
    st.markdown('---')
    st.markdown('### 🎯 自动识别的模式')
    
    type_colors = {
        'warning': ('pattern-warning', '⚠️ 风险信号'),
        'info': ('pattern-info', 'ℹ️ 观察提示'),
        'success': ('pattern-success', '✅ 良好表现')
    }
    
    for p in patterns:
        cls, label = type_colors.get(p['type'], ('pattern-info', p['type']))
        st.markdown(f"""
        <div class="pattern-card {cls}">
            <div style="font-weight:600;margin-bottom:4px">{label}：{p['title']}</div>
            <div style="color:#374151;font-size:0.95rem">{p['detail']}</div>
        </div>
        """, unsafe_allow_html=True)

elif analysis_mode == '深度模式分析':
    st.markdown('### 🔬 深度模式挖掘')
    
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(plot_milk_analysis(filtered_df), use_container_width=True)
    with c2:
        st.plotly_chart(plot_age_comparison(filtered_df), use_container_width=True)
    
    st.plotly_chart(plot_weekly_pattern(filtered_df), use_container_width=True)
    
    st.markdown('---')
    st.markdown('#### 📐 变量相关性分析')
    
    corr = compute_correlations(filtered_df)
    if not corr.empty:
        corr_cn = corr.rename(columns={
            'age_months': '月龄', 'bedtime_minutes': '入睡时间',
            'naps_count': '小睡次数', 'total_nap_minutes': '小睡总时长',
            'milk_amount_ml': '奶量', 'nightwakings': '夜醒次数',
            'night_sleep_minutes': '夜间睡眠', 'total_sleep_minutes': '总睡眠'
        }, index={
            'age_months': '月龄', 'bedtime_minutes': '入睡时间',
            'naps_count': '小睡次数', 'total_nap_minutes': '小睡总时长',
            'milk_amount_ml': '奶量', 'nightwakings': '夜醒次数',
            'night_sleep_minutes': '夜间睡眠', 'total_sleep_minutes': '总睡眠'
        })
        st.dataframe(corr_cn.style.background_gradient(cmap='RdBu_r', vmin=-1, vmax=1), 
                     use_container_width=True, height=420)
        st.caption('红色=正相关，蓝色=负相关；绝对值越接近1相关性越强')
    else:
        st.info('数据不足，无法进行相关性分析')
    
    st.markdown('---')
    st.markdown('#### 📋 各组统计对比')
    
    group_opts = [('按月龄', 'age_group'), ('按入睡时段', 'bedtime_group'),
                  ('按小睡次数', 'naps_group'), ('按奶量区间', 'milk_group')]
    sel_group = st.selectbox('选择分组维度', [g[0] for g in group_opts])
    sel_col = dict(group_opts)[sel_group]
    
    targets = ['night_sleep_hours', 'total_sleep_hours', 'nightwakings', 'naps_count']
    targets = [t for t in targets if t in filtered_df.columns]
    gs = compute_group_stats(filtered_df, sel_col, targets)
    
    if not gs.empty:
        cn_map = {'night_sleep_hours': '夜间睡眠', 'total_sleep_hours': '总睡眠',
                  'nightwakings': '夜醒', 'naps_count': '小睡次数',
                  'mean': '平均', 'std': '标准差', 'count': '样本数'}
        gs_display = gs.rename(columns=lambda x: cn_map.get(x, x))
        for old in list(gs.columns):
            if old != sel_col:
                parts = old.rsplit('_', 1)
                if len(parts) == 2:
                    base, stat = parts
                    gs_display = gs_display.rename(columns={
                        old: f'{cn_map.get(base, base)} {cn_map.get(stat, stat)}'
                    })
        gs_display = gs_display.rename(columns={sel_col: '分组'})
        st.dataframe(gs_display.style.highlight_max(axis=0, subset=[c for c in gs_display.columns if '平均' in c and '夜醒' not in c])
                     .highlight_min(axis=0, subset=[c for c in gs_display.columns if '夜醒' in c and '平均' in c]),
                     use_container_width=True)

elif analysis_mode == '分组对比分析':
    st.markdown('### 🧩 多维分组对比')
    
    age_group_mode = filtered_df['age_group'].mode().iloc[0] if filtered_df['age_group'].notna().any() else ''
    norm_results = compare_to_norms(
        age_group_mode,
        stats.get('avg_total_sleep_hours'),
        stats.get('avg_night_sleep_hours'),
        stats.get('avg_naps_count')
    )
    
    if norm_results:
        st.markdown('#### 📏 与睡眠标准对比')
        cn1, cn2, cn3 = st.columns(3)
        for i, (label, status, detail) in enumerate(norm_results):
            col = [cn1, cn2, cn3][i % 3]
            with col:
                if status == '正常':
                    st.success(f'✅ {label}：{detail}')
                elif status == '偏低':
                    st.warning(f'⚠️ {label}：{detail}')
                else:
                    st.info(f'ℹ️ {label}：{detail}')
    
    st.markdown('---')
    
    st.markdown('#### 📊 睡眠时长：按月龄 × 喂养方式')
    try:
        pivot_sleep = filtered_df.pivot_table(
            values='total_sleep_hours', index='age_group', columns='feeding_type',
            aggfunc='mean'
        ).round(1)
        if len(pivot_sleep) > 0:
            st.dataframe(pivot_sleep.style.background_gradient(axis=1, cmap='YlGn'),
                         use_container_width=True)
    except:
        st.info('数据不足')
    
    st.markdown('#### 📊 夜醒次数：按月龄 × 是否长牙')
    try:
        pivot_nw = filtered_df.pivot_table(
            values='nightwakings', index='age_group', columns='teething',
            aggfunc='mean'
        ).round(2)
        if len(pivot_nw) > 0:
            st.dataframe(pivot_nw.style.background_gradient(axis=1, cmap='Reds'),
                         use_container_width=True)
    except:
        st.info('数据不足')
    
    st.markdown('#### 📊 夜醒频率：按天气 × 奶量区间')
    try:
        pivot_milk = filtered_df.pivot_table(
            values='nightwakings', index='weather', columns='milk_group',
            aggfunc='mean'
        ).round(2)
        pivot_milk = pivot_milk.drop('未知', axis=1, errors='ignore').drop('未知', axis=0, errors='ignore')
        if len(pivot_milk) > 0:
            st.dataframe(pivot_milk.style.background_gradient(axis=1, cmap='OrRd'),
                         use_container_width=True)
    except:
        st.info('数据不足')

elif analysis_mode == '睡眠节律建议':
    st.markdown('### 💡 个性化节律建议')
    
    bw = advice.get('bedtime_window', {})
    if bw:
        cur = bw.get('current', {})
        rec = bw.get('recommended', {})
        
        st.markdown('<div class="section-title">🛌 入睡窗口分析</div>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown(f"""
            <div class="advice-card">
                <div style="font-size:0.9em;color:#6366F1;font-weight:600">当前实际</div>
                <div style="font-size:1.6rem;font-weight:700;margin:0.5rem 0">{cur.get('avg', '')}</div>
                <div>建议波动范围：{cur.get('window', '')}</div>
                <div style="margin-top:0.6rem">{cur.get('consistency', '')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_b:
            st.markdown(f"""
            <div class="advice-card" style="background:#ECFDF5;border-color:#6EE7B7">
                <div style="font-size:0.9em;color:#059669;font-weight:600">🏆 推荐窗口</div>
                <div style="font-size:1.6rem;font-weight:700;margin:0.5rem 0">{rec.get('window', '')}</div>
                <div style="font-size:0.85em;color:#047857">💡 {rec.get('reason', '')}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">⚡ 优先行动项（按优先级排序）</div>', unsafe_allow_html=True)
    for pa in sorted(advice.get('priority_actions', []), 
                     key=lambda x: {'high': 0, 'medium': 1, 'low': 2}[x.get('level', 'low')]):
        st.markdown(f"""
        <div class="priority-{pa['level']}">
            <div style="font-weight:600">{pa['action']}</div>
            <div style="font-size:0.9em;margin-top:4px">{pa['detail']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    nap_tips = advice.get('nap_adjustment', [])
    if nap_tips:
        st.markdown('<div class="section-title">😴 白天小睡调整提示</div>', unsafe_allow_html=True)
        for tip in nap_tips:
            st.markdown(f'<div style="padding:0.6rem 0.8rem;background:#FEF3C7;border-radius:8px;margin:0.3rem 0">{tip}</div>',
                        unsafe_allow_html=True)
    
    gen_tips = advice.get('general_tips', [])
    if gen_tips:
        st.markdown('<div class="section-title">📝 综合分析提示</div>', unsafe_allow_html=True)
        for tip in gen_tips:
            st.markdown(f'<div style="padding:0.5rem 0.8rem;background:#F8FAFC;border-left:3px solid #6366F1;margin:0.3rem 0">{tip}</div>',
                        unsafe_allow_html=True)
    
    st.markdown('---')
    st.markdown('<div class="section-title">📄 导出阶段性睡眠报告</div>', unsafe_allow_html=True)
    
    if st.button('📥 生成并下载 Excel 报告', type='primary', use_container_width=True):
        with st.spinner('正在生成报告...'):
            report_io = export_report_to_excel(
                filtered_df, stats, stability, patterns, advice,
                quality_result=data_quality_result
            )
            st.success('✅ 报告生成成功！')
            
            st.download_button(
                label='⬇️ 下载分析报告 (.xlsx)',
                data=report_io,
                file_name=f'宝宝睡眠分析报告_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True
            )
    
    with st.expander('👀 预览报告包含内容'):
        st.markdown("""
        **Sheet 1：概览报告**
        - 核心指标汇总（睡眠时长、夜醒、作息规律等）
        - 作息稳定度详情（入睡/起床/小睡三维评估）
        - 模式识别结果（自动发现的睡眠规律与问题）
        - 节律调整建议（入睡窗口、小睡调整、优先行动）
        
        **Sheet 2：每日原始数据**
        - 清洗后的完整每日记录（含计算字段）
        
        **Sheet 3：分组统计**
        - 按月龄/入睡时段/小睡次数/奶量区间/喂养方式的均值统计
        
        **Sheet 4：数据质量与异常记录**
        - 数据质量评分与概览
        - 各字段异常统计
        - 异常记录明细（原始值、修正值、是否纳入统计、异常原因、影响字段）
        """)

st.markdown('---')
with st.expander('🔎 查看原始数据详情'):
    display_cols = ['date', 'age_months', 'age_group', 'bedtime', 'wakeup_time',
                    'night_sleep_hours', 'nap_hours', 'total_sleep_hours',
                    'nightwakings', 'naps_count', 'milk_amount_ml',
                    'feeding_type', 'teething', 'weather']
    display_cols = [c for c in display_cols if c in filtered_df.columns]
    
    df_display = filtered_df[display_cols].copy()
    df_display['date'] = df_display['date'].dt.strftime('%Y-%m-%d')
    df_display = df_display.round(1)
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    st.caption(f'共 {len(df_display)} 条记录')
