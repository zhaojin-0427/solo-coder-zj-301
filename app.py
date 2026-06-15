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
    plot_milk_analysis, plot_age_comparison, plot_weekly_pattern,
    plot_intervention_comparison, plot_prediction_trend,
    plot_dimension_effects, plot_stability_prediction
)
from advisor import generate_sleep_advice, export_report_to_excel
from data_quality import analyze_data_quality, get_filtered_df
from intervention_params import (
    get_default_intervention_params, validate_params,
    get_param_display, SIM_DURATION_OPTIONS, SOOTHING_STRATEGY_LEVELS,
    bedtime_minutes_to_hm, hm_to_bedtime_minutes
)
from prediction_engine import (
    compute_baseline_metrics, compute_intervention_effects,
    compute_combined_prediction, generate_daily_prediction_series,
    generate_risk_warnings, compute_action_priority
)
from plan_generator import (
    generate_daily_plan, generate_intervention_calendar,
    generate_execution_summary, generate_baseline_summary
)
from intervention_exporter import export_intervention_plan_to_excel
from phase_analyzer import (
    PHASE_MODES, generate_phase_options, filter_by_phase,
    compute_phase_metrics, compare_phases, generate_phase_summary,
    compute_intervention_vs_prediction
)
from phase_visualizer import (
    plot_phase_metrics_comparison, plot_phase_trend_comparison,
    plot_phase_nw_periods_comparison, plot_phase_radar,
    plot_milk_nw_correlation_comparison, plot_prediction_vs_actual,
    plot_phase_status_timeline
)
from phase_exporter import export_phase_review_to_excel
from care_routes import render_care_center


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
        ['总览仪表盘', '深度模式分析', '分组对比分析', '睡眠节律建议', '睡眠干预模拟器', '睡眠复盘与阶段对比中心', '照护协同与交接记录中心'],
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

elif analysis_mode == '睡眠干预模拟器':
    st.markdown('### 🎯 睡眠干预方案模拟器')
    st.caption('基于历史数据预测干预效果，生成个性化睡眠改善方案')
    
    baseline = compute_baseline_metrics(filtered_df)
    
    if 'intervention_params' not in st.session_state:
        default_params = get_default_intervention_params(filtered_df, stats, stability, patterns)
        st.session_state.intervention_params = default_params
    
    params = st.session_state.intervention_params
    
    col_param_editor, col_result_view = st.columns([1, 2])
    
    with col_param_editor:
        st.markdown('<div class="section-title">⚙️ 干预参数设置</div>', unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown('**📅 模拟周期**')
            sim_days = st.select_slider(
                '选择模拟天数',
                options=SIM_DURATION_OPTIONS,
                value=params.get('sim_duration_days', 14),
                help='选择未来多少天的干预模拟'
            )
            params['sim_duration_days'] = sim_days
        
        with st.container(border=True):
            st.markdown('**🛌 目标入睡窗口**')
            
            bt_start_default = int(params.get('target_bedtime_start', -120))
            bt_end_default = int(params.get('target_bedtime_end', -90))
            
            bt_start_h, bt_start_m = bedtime_minutes_to_hm(bt_start_default)
            bt_end_h, bt_end_m = bedtime_minutes_to_hm(bt_end_default)
            
            col_bt_s, col_bt_e = st.columns(2)
            with col_bt_s:
                bt_start_str = st.time_input(
                    '窗口开始',
                    value=datetime(2024, 1, 1, bt_start_h, bt_start_m).time(),
                    help='建议入睡窗口的最早时间'
                )
            with col_bt_e:
                bt_end_str = st.time_input(
                    '窗口结束',
                    value=datetime(2024, 1, 1, bt_end_h, bt_end_m).time(),
                    help='建议入睡窗口的最晚时间'
                )
            
            bt_start_min = hm_to_bedtime_minutes(bt_start_str.hour, bt_start_str.minute)
            bt_end_min = hm_to_bedtime_minutes(bt_end_str.hour, bt_end_str.minute)
            
            params['target_bedtime_start'] = int(bt_start_min)
            params['target_bedtime_end'] = int(bt_end_min)
        
        with st.container(border=True):
            st.markdown('**⏰ 最后一觉最晚结束时间**')
            
            ln_default = params.get('last_nap_deadline', 15 * 60)
            ln_h = ln_default // 60
            ln_m = ln_default % 60
            
            last_nap_time = st.time_input(
                '选择时间',
                value=datetime(2024, 1, 1, ln_h, ln_m).time(),
                help='白天最后一觉必须在此时间前结束'
            )
            params['last_nap_deadline'] = int(last_nap_time.hour * 60 + last_nap_time.minute)
        
        with st.container(border=True):
            st.markdown('**😴 白天小睡次数调整**')
            nap_adj = st.slider(
                '小睡次数变化',
                min_value=-2,
                max_value=2,
                value=params.get('nap_count_adjustment', 0),
                step=1,
                help='相对于当前平均小睡次数的增减'
            )
            params['nap_count_adjustment'] = nap_adj
            current_naps = baseline.get('avg_naps_count', 0)
            target_naps = current_naps + nap_adj
            st.caption(f'当前平均: {current_naps:.1f} 次 → 目标: {target_naps:.1f} 次')
        
        with st.container(border=True):
            st.markdown('**🍼 睡前奶量变化**')
            milk_pct = st.slider(
                '奶量变化百分比',
                min_value=-30,
                max_value=30,
                value=params.get('milk_change_pct', 0),
                step=5,
                help='相对于当前平均奶量的变化比例'
            )
            params['milk_change_pct'] = milk_pct
            current_milk = baseline.get('avg_milk_ml', 0)
            if current_milk and current_milk > 0:
                target_milk = current_milk * (1 + milk_pct / 100)
                st.caption(f'当前平均: {current_milk:.0f} ml → 目标: {target_milk:.0f} ml')
            else:
                st.caption('暂无奶量数据')
        
        with st.container(border=True):
            st.markdown('**💆 夜醒安抚策略强度**')
            strategy_options = list(SOOTHING_STRATEGY_LEVELS.keys())
            strategy = st.select_slider(
                '选择安抚策略',
                options=strategy_options,
                value=params.get('soothing_strategy', '适度安抚'),
                help='不同策略对夜醒改善效果不同，风险也不同'
            )
            params['soothing_strategy'] = strategy
            strat_info = SOOTHING_STRATEGY_LEVELS[strategy]
            st.caption(f"强度: {'★' * strat_info['intensity']}{'☆' * (3 - strat_info['intensity'])}")
            st.caption(strat_info['description'])
        
        st.session_state.intervention_params = params
        
        errors = validate_params(params)
        if errors:
            for err in errors:
                st.warning(err)
    
    params_valid = len(validate_params(params)) == 0
    
    with col_result_view:
        if not params_valid:
            st.info('⚠️ 请先修正左侧参数中的错误，然后查看预测结果')
            st.stop()
        
        effects = compute_intervention_effects(filtered_df, baseline, params)
        prediction = compute_combined_prediction(baseline, effects, params)
        daily_series = generate_daily_prediction_series(baseline, effects, params)
        risks = generate_risk_warnings(baseline, effects, params)
        priorities = compute_action_priority(filtered_df, baseline, effects, params)
        
        param_display = get_param_display(params, stats)
        
        st.markdown('<div class="section-title">📊 干预前后对比预测</div>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            nw_change = prediction['changes']['night_waking_reduction_abs']
            st.metric(
                '夜醒次数',
                f"{prediction['predicted']['avg_nightwakings']:.2f} 次",
                delta=f"{nw_change:+.2f} 次 ({prediction['changes']['night_waking_reduction_pct']:+.1f}%)",
                delta_color='inverse' if nw_change < 0 else 'normal'
            )
        with c2:
            sleep_change = prediction['changes']['total_sleep_change_minutes']
            st.metric(
                '总睡眠时长',
                f"{prediction['predicted']['avg_total_sleep_hours']:.1f} h",
                delta=f"{sleep_change:+.0f} 分钟 ({prediction['changes']['total_sleep_change_pct']:+.1f}%)",
                delta_color='normal' if sleep_change >= 0 else 'inverse'
            )
        with c3:
            stab_gain = prediction['changes']['stability_gain']
            st.metric(
                '作息稳定度',
                f"{prediction['predicted']['stability_score']:.0f} 分",
                delta=f"{stab_gain:+.1f} 分",
                delta_color='normal' if stab_gain >= 0 else 'inverse'
            )
        
        st.plotly_chart(plot_intervention_comparison(prediction), use_container_width=True)
        
        tab1, tab2, tab3 = st.tabs(['📈 预测趋势', '🧩 维度分析', '⭐ 执行优先级'])
        
        with tab1:
            st.plotly_chart(plot_prediction_trend(daily_series), use_container_width=True)
            st.plotly_chart(plot_stability_prediction(daily_series), use_container_width=True)
        
        with tab2:
            st.plotly_chart(plot_dimension_effects(prediction['dimension_effects']), use_container_width=True)
            
            st.markdown('#### 📋 各维度详情')
            for key, dim in prediction['dimension_effects'].items():
                risk_label = {'low': '🟢 低风险', 'medium': '🟡 中风险', 'high': '🔴 高风险'}.get(dim['risk_level'], '低风险')
                with st.expander(f"{dim['icon']} {dim['name']} - {risk_label}"):
                    st.write(f"夜醒改善贡献: {dim['nw_reduction_pct_contribution']:+.1f}%")
                    st.write(f"睡眠时长贡献: {dim['sleep_change_contribution']:+.0f} 分钟")
                    st.write(f"稳定度贡献: {dim['stability_contribution']:+.1f} 分")
                    st.write(f"有效性: {dim['effectiveness']*100:.0f}%")
        
        with tab3:
            st.markdown('#### 🏆 按影响程度排序')
            for p in priorities:
                priority_class = f"priority-{p['priority']}"
                st.markdown(f"""
                <div class="{priority_class}">
                    <div style="font-weight:600">{p['icon']} {p['name']} - {p['priority_label']}</div>
                    <div style="font-size:0.9em;margin-top:4px">
                        夜醒影响: {p['night_waking_impact_pct']:.1f}% | 
                        睡眠影响: {p['sleep_impact_minutes']:+.0f} 分钟 | 
                        综合得分: {p['score']:.1f}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown('<div class="section-title">⚠️ 风险提示</div>', unsafe_allow_html=True)
        for risk in risks:
            risk_color = {'high': '#DC2626', 'medium': '#F59E0B', 'low': '#22C55E'}.get(risk['level'], '#6B7280')
            risk_bg = {'high': '#FEF2F2', 'medium': '#FFFBEB', 'low': '#F0FDF4'}.get(risk['level'], '#F8FAFC')
            st.markdown(f"""
            <div style="background:{risk_bg};padding:0.8rem 1rem;border-radius:8px;border-left:4px solid {risk_color};margin:0.4rem 0">
                <div style="font-weight:600;color:{risk_color}">{risk['title']}</div>
                <div style="font-size:0.9em;color:#374151;margin-top:4px">{risk['detail']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        daily_plan = generate_daily_plan(baseline, params, prediction, priorities)
        calendar_df = generate_intervention_calendar(daily_plan)
        execution_summary = generate_execution_summary(baseline, params, prediction, priorities, risks)
        baseline_summary = generate_baseline_summary(baseline, stats)
        
        st.markdown('<div class="section-title">📅 干预日历表</div>', unsafe_allow_html=True)
        
        phase_colors = {
            '适应期': '#F0F9FF',
            '调整期': '#FEF3C7',
            '巩固期': '#D1FAE5',
            '稳定期': '#E0E7FF',
        }
        
        cal_display = calendar_df.copy()
        cal_display = cal_display[['日期', '天数', '阶段', '入睡窗口', '最后一觉截止', '小睡目标', '奶量目标', '预计夜醒']]
        
        def highlight_phase(row):
            phase = row.get('阶段', '')
            color = phase_colors.get(phase, '#FFFFFF')
            return [f'background-color: {color}'] * len(row)
        
        st.dataframe(
            cal_display.style.apply(highlight_phase, axis=1),
            use_container_width=True,
            hide_index=True,
            height=380
        )
        
        st.markdown('<div class="section-title">📄 导出干预计划</div>', unsafe_allow_html=True)
        st.caption('导出完整的干预方案Excel报告，包含基线摘要、干预参数、预测结果、每日执行建议和风险说明')
        
        if st.button('📥 生成并下载干预方案报告', type='primary', use_container_width=True, key='export_intervention'):
            with st.spinner('正在生成干预方案报告...'):
                report_io = export_intervention_plan_to_excel(
                    filtered_df, baseline, params, prediction,
                    daily_plan, calendar_df, priorities, risks,
                    execution_summary, baseline_summary, param_display
                )
                st.success('✅ 干预方案报告生成成功！')
                
                st.download_button(
                    label='⬇️ 下载干预方案报告 (.xlsx)',
                    data=report_io,
                    file_name=f'宝宝睡眠干预方案_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    use_container_width=True
                )
        
        with st.expander('👀 预览报告包含内容'):
            st.markdown("""
            **Sheet 1：干预计划概览**
            - 基线摘要（当前睡眠状况）
            - 干预参数设置
            - 预测结果对比（干预前后）
            - 各维度影响分析
            - 执行优先级排序
            - 风险提示
            
            **Sheet 2：干预日历表**
            - 按天的执行日历
            - 分阶段显示（适应期/调整期/巩固期/稳定期）
            - 每日目标参数
            
            **Sheet 3：每日执行建议**
            - 每天的详细执行指南
            - 关键任务清单
            - 注意事项
            
            **Sheet 4：风险与注意事项**
            - 风险提示明细
            - 执行注意事项
            - 紧急情况处理
            """)

elif analysis_mode == '睡眠复盘与阶段对比中心':
    st.markdown('### 📋 睡眠复盘与阶段对比中心')
    st.caption('按自然周/月份/自定义阶段/干预前后生成睡眠复盘，对比不同阶段的指标变化，识别改善趋势')
    
    st.markdown("""
    <style>
    .phase-card {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
        border-left: 4px solid #6366F1;
    }
    .phase-status-improving { border-color: #10B981; background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); }
    .phase-status-regressing { border-color: #EF4444; background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); }
    .phase-status-fluctuating { border-color: #F59E0B; background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%); }
    .phase-status-stable { border-color: #059669; background: linear-gradient(135deg, #ecfdf5 0%, #a7f3d0 100%); }
    .phase-status-insufficient { border-color: #9CA3AF; background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%); }
    </style>
    """, unsafe_allow_html=True)
    
    phase_mode = st.selectbox(
        '📅 阶段划分方式',
        PHASE_MODES,
        index=0,
        help='选择如何划分对比阶段'
    )
    
    custom_phases = []
    pre_intervention_dates = None
    post_intervention_dates = None
    intervention_split_date = None
    
    if phase_mode == '自定义阶段':
        st.markdown('<div class="section-title">✏️ 自定义阶段</div>', unsafe_allow_html=True)
        
        if 'custom_phase_count' not in st.session_state:
            st.session_state.custom_phase_count = 2
        
        col_p1, col_p2 = st.columns([3, 1])
        with col_p2:
            phase_count = st.number_input(
                '阶段数量', 
                min_value=2, max_value=6, 
                value=st.session_state.custom_phase_count
            )
            st.session_state.custom_phase_count = phase_count
        
        min_date = filtered_df['date'].min().date()
        max_date = filtered_df['date'].max().date()
        
        for i in range(phase_count):
            st.markdown(f'**阶段 {i+1}**')
            c1, c2, c3 = st.columns([2, 2, 2])
            with c1:
                p_name = st.text_input(
                    f'阶段名称',
                    value=f'阶段{i+1}',
                    key=f'phase_name_{i}'
                )
            with c2:
                p_start = st.date_input(
                    f'开始日期',
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date,
                    key=f'phase_start_{i}'
                )
            with c3:
                p_end = st.date_input(
                    f'结束日期',
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date,
                    key=f'phase_end_{i}'
                )
            custom_phases.append({
                'name': p_name,
                'start_date': p_start,
                'end_date': p_end
            })
    
    elif phase_mode == '干预前后':
        st.markdown('<div class="section-title">🎯 干预阶段设置</div>', unsafe_allow_html=True)
        
        min_date = filtered_df['date'].min().date()
        max_date = filtered_df['date'].max().date()
        mid_date = min_date + (max_date - min_date) // 2
        
        intervention_split_date = st.date_input(
            '选择干预开始日期',
            value=mid_date,
            min_value=min_date,
            max_value=max_date,
            help='此日期之前为干预前（基线），之后为干预后'
        )
        
        mark_as_intervention = st.checkbox(
            '⭐ 将「干预后」标记为干预阶段，与干预模拟器预测结果对比',
            value=False,
            help='启用后可选择干预模拟器的预测结果进行实际效果对比'
        )
    
    phase_options = generate_phase_options(filtered_df, phase_mode, custom_phases)
    
    if phase_mode == '干预前后' and intervention_split_date:
        for po in phase_options:
            if po['type'] == 'pre_intervention':
                po['start_date'] = min_date
                po['end_date'] = intervention_split_date - timedelta(days=1)
            elif po['type'] == 'post_intervention':
                po['start_date'] = intervention_split_date
                po['end_date'] = max_date
    
    if phase_options:
        selected_phases = st.multiselect(
            '选择要对比的阶段（至少选2个）',
            options=[p['name'] for p in phase_options],
            default=[p['name'] for p in phase_options[:min(2, len(phase_options))]]
        )
        
        if len(selected_phases) >= 2:
            selected_phase_configs = [p for p in phase_options if p['name'] in selected_phases]
            selected_phase_configs.sort(key=lambda x: x.get('start_date') or datetime.min.date())
            
            phase_results = []
            df_phases_dict = {}
            
            for pc in selected_phase_configs:
                df_phase = filter_by_phase(filtered_df, pc['start_date'], pc['end_date'])
                df_phases_dict[pc['name']] = df_phase
                pr = compute_phase_metrics(df_phase, pc['name'])
                phase_results.append(pr)
            
            comparison = compare_phases(phase_results)
            summary = generate_phase_summary(phase_results, comparison)
            
            st.plotly_chart(plot_phase_status_timeline(phase_results), use_container_width=True)
            
            st.markdown('<div class="section-title">📊 各阶段核心指标对比</div>', unsafe_allow_html=True)
            
            metric_cols = st.columns(4)
            display_metrics = [
                ('avg_total_sleep_hours', '总睡眠', 'h/天'),
                ('avg_night_sleep_hours', '夜间睡眠', 'h'),
                ('avg_nightwakings', '夜醒次数', '次'),
                ('bedtime_window_stability', '入睡稳定度', '分'),
            ]
            
            for i, (m_key, m_label, m_unit) in enumerate(display_metrics):
                with metric_cols[i]:
                    vals = []
                    for pr in phase_results:
                        v = pr['metrics'].get(m_key, 0) or 0
                        vals.append(round(v, 2))
                    
                    if len(vals) >= 2:
                        delta = vals[-1] - vals[0]
                        delta_pct = (delta / max(vals[0], 0.01)) * 100
                        if m_key == 'avg_nightwakings':
                            delta_color = 'inverse' if delta < 0 else 'normal'
                        else:
                            delta_color = 'normal' if delta >= 0 else 'inverse'
                        
                        st.metric(
                            m_label,
                            f'{vals[-1]} {m_unit}',
                            delta=f'{delta:+.2f} ({delta_pct:+.1f}%)',
                            delta_color=delta_color
                        )
                    else:
                        st.metric(m_label, f'{vals[0]} {m_unit}' if vals else '-')
            
            st.plotly_chart(plot_phase_metrics_comparison(phase_results), use_container_width=True)
            
            st.markdown('---')
            st.markdown('<div class="section-title">📈 趋势与维度分析</div>', unsafe_allow_html=True)
            
            tab1, tab2, tab3, tab4 = st.tabs([
                '📊 阶段内趋势对照', '🔥 夜醒时段变化', 
                '🎯 综合质量雷达', '🍼 奶量关联分析'
            ])
            
            with tab1:
                st.plotly_chart(plot_phase_trend_comparison(df_phases_dict, [pr['phase_name'] for pr in phase_results]), use_container_width=True)
            
            with tab2:
                st.plotly_chart(plot_phase_nw_periods_comparison(phase_results), use_container_width=True)
            
            with tab3:
                st.plotly_chart(plot_phase_radar(phase_results), use_container_width=True)
            
            with tab4:
                st.plotly_chart(plot_milk_nw_correlation_comparison(phase_results), use_container_width=True)
                st.caption('💡 相关系数为负表示奶量越多夜醒越少，是正常健康的关联')
            
            st.markdown('---')
            
            intervention_comp = None
            if phase_mode == '干预前后':
                post_phases = [pr for pr in phase_results if '干预后' in pr['phase_name']]
                pre_phases = [pr for pr in phase_results if '干预前' in pr['phase_name']]
                
                if mark_as_intervention and post_phases and pre_phases:
                    st.markdown('<div class="section-title">🎯 干预实际效果 vs 预测对比</div>', unsafe_allow_html=True)
                    
                    if 'intervention_params' in st.session_state and 'prediction_result' not in st.session_state:
                        from prediction_engine import compute_baseline_metrics, compute_intervention_effects, compute_combined_prediction
                        params = st.session_state.intervention_params
                        pre_df = df_phases_dict.get(pre_phases[0]['phase_name'], filtered_df)
                        baseline = compute_baseline_metrics(pre_df)
                        effects = compute_intervention_effects(pre_df, baseline, params)
                        prediction_result = compute_combined_prediction(baseline, effects, params)
                        st.session_state.prediction_result = prediction_result
                    
                    if 'prediction_result' in st.session_state and post_phases:
                        post_df = df_phases_dict.get(post_phases[0]['phase_name'])
                        intervention_comp = compute_intervention_vs_prediction(post_df, st.session_state.prediction_result)
                        
                        st.plotly_chart(plot_prediction_vs_actual(intervention_comp), use_container_width=True)
                        
                        col_a, col_b, col_c = st.columns(3)
                        for i, (key, label) in enumerate([
                            ('nightwakings', '夜醒改善达成率'),
                            ('total_sleep_hours', '睡眠增长达成率'),
                            ('stability_score', '稳定度提升达成率')
                        ]):
                            data = intervention_comp.get(key, {})
                            achievement = data.get('achievement_pct', 0)
                            cols = [col_a, col_b, col_c]
                            with cols[i]:
                                if achievement >= 80:
                                    st.success(f'✅ {label}: {achievement}%')
                                elif achievement >= 50:
                                    st.warning(f'📊 {label}: {achievement}%')
                                else:
                                    st.error(f'⚠️ {label}: {achievement}%')
                    else:
                        st.info('💡 请先在「睡眠干预模拟器」中设置参数并生成预测，然后返回此处进行对比')
            
            st.markdown('---')
            st.markdown('<div class="section-title">📝 关键变化摘要与复盘建议</div>', unsafe_allow_html=True)
            
            overall_assessment = summary.get('overall_assessment', '')
            if '改善' in overall_assessment:
                status_class = 'phase-status-improving'
            elif '倒退' in overall_assessment:
                status_class = 'phase-status-regressing'
            elif '波动' in overall_assessment:
                status_class = 'phase-status-fluctuating'
            elif '稳定' in overall_assessment:
                status_class = 'phase-status-stable'
            else:
                status_class = 'phase-status-insufficient'
            
            st.markdown(f"""
            <div class="phase-card {status_class}">
                <div style="font-size:1.1rem;font-weight:600;margin-bottom:8px">{overall_assessment}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown('#### 🔍 关键变化')
            for change in summary.get('key_changes', []):
                st.markdown(f'- {change}')
            
            st.markdown('#### 💡 下一阶段建议')
            for rec in summary.get('recommendations', []):
                st.markdown(f'- {rec}')
            
            st.markdown('---')
            st.markdown('<div class="section-title">📄 导出阶段复盘报告</div>', unsafe_allow_html=True)
            
            filters_info = {
                '月龄阶段': filter_age,
                '喂养方式': filter_feeding,
                '是否长牙': filter_teething,
                '天气': filter_weather,
                '日期范围': f'{date_range[0]} ~ {date_range[1]}' if date_range and len(date_range) == 2 else ('全部' if not date_range else str(date_range[0])),
                '排除异常记录': '是' if exclude_anomalies else '否'
            }
            
            if st.button('📥 生成并下载阶段复盘 Excel 报告', type='primary', use_container_width=True):
                with st.spinner('正在生成阶段复盘报告...'):
                    report_io = export_phase_review_to_excel(
                        phase_results, comparison, summary,
                        df_phases_dict, intervention_comp,
                        data_quality_result, filters_info
                    )
                    st.success('✅ 阶段复盘报告生成成功！')
                    
                    st.download_button(
                        label='⬇️ 下载阶段复盘报告 (.xlsx)',
                        data=report_io,
                        file_name=f'宝宝睡眠阶段复盘报告_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        use_container_width=True
                    )
            
            with st.expander('👀 预览报告包含内容'):
                st.markdown("""
                **Sheet 1：阶段复盘概览**
                - 阶段定义（名称、日期范围、记录天数、状态标记）
                - 筛选条件说明
                - 核心指标对比（各阶段睡眠、夜醒、作息等指标并列对比）
                - 作息稳定度对比
                - 夜醒时段分布对比
                - 奶量与夜醒关联变化
                - 干预实际效果与预测偏差（如启用干预对比）
                
                **Sheet 2：趋势对比数据**
                - 各阶段每日原始数据（日期、睡眠时长、夜醒、奶量等）
                - 用于生成趋势对照图的数据明细
                
                **Sheet 3：关键变化与建议**
                - 整体评估（改善中/反复波动/阶段倒退/稳定良好等）
                - 关键变化摘要
                - 下一阶段建议
                - 详细指标变化对比
                - 异常记录影响说明
                """)
        else:
            st.info('👆 请至少选择2个阶段进行对比分析')
    else:
        st.warning('当前筛选条件下数据不足以生成阶段，请调整筛选或增加数据记录')

elif analysis_mode == '照护协同与交接记录中心':
    render_care_center(
        filtered_df, processed_df, exclude_anomalies,
        filter_age, filter_feeding, filter_teething, filter_weather, date_range
    )

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
