import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from care_data_processor import (
    load_care_csv, preprocess_care_data, filter_care_data,
    create_care_record, add_care_records_to_df, generate_sample_care_data,
    CAREGIVER_TYPES, BEDTIME_ROUTINE_ITEMS, SOOTHING_METHODS, NW_RESPONSES,
)
from care_analyzer import (
    compute_handover_timeline, compute_routine_completion,
    compute_nw_response_diff, compute_intervention_deviation,
    compute_consistency_score, detect_care_patterns, compute_care_summary,
)
from care_visualizer import (
    plot_handover_timeline, plot_routine_completion,
    plot_nw_response_diff, plot_consistency_gauge, plot_consistency_radar,
    plot_intervention_deviation, plot_routine_items_frequency,
    plot_caregiver_sleep_correlation,
)
from care_exporter import export_care_report_to_excel


def render_care_center(filtered_df, processed_df, exclude_anomalies, filter_age, filter_feeding, filter_teething, filter_weather, date_range):
    st.markdown('### 🤝 照护协同与交接记录中心')
    st.caption('多照护人交接记录、执行一致性分析与协同建议')

    st.markdown("""
    <style>
    .care-card {
        background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
        border-left: 4px solid #3B82F6;
    }
    .care-alert-warning {
        background: #FEF2F2;
        border-left: 4px solid #EF4444;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin: 0.4rem 0;
    }
    .care-alert-info {
        background: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin: 0.4rem 0;
    }
    .care-alert-success {
        background: #ECFDF5;
        border-left: 4px solid #10B981;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin: 0.4rem 0;
    }
    .care-metric {
        background: #f8fafc;
        padding: 0.8rem 1rem;
        border-radius: 10px;
        border-left: 3px solid #3B82F6;
        margin: 0.3rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

    if 'care_df' not in st.session_state:
        st.session_state.care_df = None

    tab_data, tab_analysis, tab_charts, tab_export = st.tabs([
        '📝 照护记录管理', '📊 交接一致性分析', '📈 可视化图表', '📄 导出报告'
    ])

    with tab_data:
        _render_data_management(filtered_df)

    care_df = st.session_state.care_df
    if care_df is None or len(care_df) == 0:
        st.info('👆 请先在「照护记录管理」中添加或导入照护记录')
        return

    care_filtered = filter_care_data(
        care_df,
        caregiver=st.session_state.get('filter_caregiver', '全部'),
        age_group=filter_age,
        feeding_type=filter_feeding,
        teething=filter_teething,
        weather=filter_weather,
        date_range=date_range,
        exclude_anomalies=exclude_anomalies,
    )

    if len(care_filtered) == 0:
        st.warning('当前筛选条件下无照护记录')
        return

    timeline = compute_handover_timeline(care_filtered)
    routine_result = compute_routine_completion(care_filtered)
    nw_diff_result = compute_nw_response_diff(care_filtered)
    deviation_result = compute_intervention_deviation(care_filtered)
    consistency = compute_consistency_score(care_filtered)
    patterns = detect_care_patterns(care_filtered)
    care_summary = compute_care_summary(care_filtered)

    with tab_analysis:
        _render_analysis(care_filtered, consistency, routine_result, nw_diff_result, deviation_result, patterns, care_summary)

    with tab_charts:
        _render_charts(care_filtered, timeline, routine_result, nw_diff_result, consistency, deviation_result)

    with tab_export:
        _render_export(care_filtered, consistency, routine_result, nw_diff_result, deviation_result, patterns, care_summary, filter_age, filter_feeding, filter_teething, filter_weather, date_range, exclude_anomalies)


def _render_data_management(filtered_df):
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">📋 照护记录数据源</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('**📤 导入照护记录 CSV**')
        care_csv = st.file_uploader(
            '上传照护记录 CSV',
            type=['csv'],
            key='care_csv_upload',
            help='CSV列：日期、照护人、睡前流程执行、安抚方式、夜醒响应方式、环境变动、临时事件备注、交接备注'
        )
        if care_csv is not None:
            care_df_new, msg = load_care_csv(care_csv)
            if care_df_new is not None:
                care_df_new = preprocess_care_data(care_df_new, sleep_df=filtered_df)
                if st.session_state.care_df is not None:
                    st.session_state.care_df = pd.concat([st.session_state.care_df, care_df_new], ignore_index=True)
                    st.session_state.care_df = st.session_state.care_df.drop_duplicates(subset=['date', 'caregiver'], keep='last').reset_index(drop=True)
                else:
                    st.session_state.care_df = care_df_new
                st.success(f'✅ 导入 {len(care_df_new)} 条照护记录')
            else:
                st.error(msg)

    with c2:
        st.markdown('**🎲 使用示例照护数据**')
        if st.button('生成示例照护数据', key='gen_sample_care', use_container_width=True):
            with st.spinner('正在生成...'):
                st.session_state.care_df = generate_sample_care_data(filtered_df)
                st.success(f'✅ 生成 {len(st.session_state.care_df)} 条示例照护记录')

    st.markdown('---')
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">✏️ 按日期补充照护记录</div>', unsafe_allow_html=True)

    with st.form('add_care_record'):
        col_a, col_b = st.columns(2)
        with col_a:
            rec_date = st.date_input('日期', value=datetime.now().date())
            rec_caregiver = st.selectbox('照护人', CAREGIVER_TYPES)
        with col_b:
            rec_routine = st.multiselect('睡前流程执行项', BEDTIME_ROUTINE_ITEMS)
            rec_soothing = st.selectbox('安抚方式', SOOTHING_METHODS)

        col_c, col_d = st.columns(2)
        with col_c:
            rec_nw_resp = st.selectbox('夜醒响应方式', NW_RESPONSES)
            rec_env = st.text_input('环境变动', value='无', placeholder='如：温度变化、噪音干扰、换环境等')
        with col_d:
            rec_event = st.text_input('临时事件备注', placeholder='如：打疫苗、感冒初愈等')
            rec_handover = st.text_area('交接备注', placeholder='交接时需告知的重要信息', height=68)

        submitted = st.form_submit_button('➕ 添加照护记录', use_container_width=True)
        if submitted:
            routine_str = ','.join(rec_routine)
            new_record = create_care_record(
                date=rec_date, caregiver=rec_caregiver,
                bedtime_routine=routine_str, soothing_method=rec_soothing,
                nw_response=rec_nw_resp, env_change=rec_env,
                temp_event=rec_event, handover_note=rec_handover,
            )
            st.session_state.care_df = add_care_records_to_df(
                st.session_state.care_df, [new_record]
            )
            if filtered_df is not None:
                sleep_subset = filtered_df[['date', 'nightwakings', 'night_sleep_hours',
                                            'total_sleep_hours', 'bedtime_minutes', 'age_group',
                                            'feeding_type', 'teething', 'weather']].copy()
                sleep_subset = sleep_subset.rename(columns={
                    'nightwakings': 'sleep_nw', 'night_sleep_hours': 'sleep_night_h',
                    'total_sleep_hours': 'sleep_total_h', 'bedtime_minutes': 'sleep_bedtime_min'
                })
                existing_cols = [c for c in st.session_state.care_df.columns if c not in sleep_subset.columns or c == 'date']
                care_base = st.session_state.care_df[existing_cols] if len(existing_cols) < len(st.session_state.care_df.columns) else st.session_state.care_df
                st.session_state.care_df = care_base.merge(sleep_subset, on='date', how='left')
            st.success(f'✅ 已添加 {rec_date} {rec_caregiver} 的照护记录')

    st.markdown('---')
    st.markdown('**照护人筛选**')
    if st.session_state.care_df is not None and len(st.session_state.care_df) > 0:
        cg_options = ['全部'] + sorted(st.session_state.care_df['caregiver'].unique().tolist())
        filter_caregiver = st.selectbox('按照护人筛选', cg_options, key='filter_caregiver_select')
        st.session_state.filter_caregiver = filter_caregiver
    else:
        st.session_state.filter_caregiver = '全部'

    if st.session_state.care_df is not None and len(st.session_state.care_df) > 0:
        st.markdown('---')
        with st.expander('📋 查看当前照护记录', expanded=False):
            display_cols = ['date', 'caregiver', 'bedtime_routine', 'routine_completion_rate',
                            'soothing_method', 'nw_response', 'env_change', 'temp_event', 'handover_note']
            existing = [c for c in display_cols if c in st.session_state.care_df.columns]
            df_disp = st.session_state.care_df[existing].copy()
            df_disp['date'] = df_disp['date'].dt.strftime('%Y-%m-%d')
            rename_map = {
                'date': '日期', 'caregiver': '照护人', 'bedtime_routine': '睡前流程',
                'routine_completion_rate': '完成率(%)', 'soothing_method': '安抚方式',
                'nw_response': '夜醒响应', 'env_change': '环境变动',
                'temp_event': '临时事件', 'handover_note': '交接备注'
            }
            df_disp = df_disp.rename(columns={k: v for k, v in rename_map.items() if k in df_disp.columns})
            st.dataframe(df_disp.round(1), use_container_width=True, hide_index=True)
            st.caption(f'共 {len(df_disp)} 条照护记录')

        if st.button('🗑️ 清空所有照护记录', key='clear_care_data'):
            st.session_state.care_df = None
            st.success('已清空照护记录')

    with st.expander('📋 照护记录 CSV 格式说明'):
        st.markdown("""
        **CSV 列说明：**

        | 列名 | 示例 | 说明 |
        |------|------|------|
        | 日期 | 2025-06-01 | YYYY-MM-DD 格式 |
        | 照护人 | 妈妈 | 妈妈/爸爸/老人/保姆 |
        | 睡前流程执行 | 洗澡,换睡衣,喂奶/喝奶,调暗灯光 | 逗号分隔的流程项 |
        | 安抚方式 | 轻拍安抚 | 抱哄入睡/轻拍安抚/声音安抚/奶睡/自主入睡/摇晃安抚/陪伴入睡 |
        | 夜醒响应方式 | 延迟响应(3-5分钟) | 立即抱起/延迟响应(3-5分钟)/延迟响应(5-10分钟)/声音安抚/轻拍安抚/喂奶安抚/陪伴等待/不干预 |
        | 环境变动 | 无 | 温度变化/噪音干扰/出差换环境/换床换房间等 |
        | 临时事件备注 | | 打疫苗/感冒初愈/换新奶粉等 |
        | 交接备注 | | 交接时需传达的关键信息 |
        """)


def _render_analysis(care_df, consistency, routine_result, nw_diff_result, deviation_result, patterns, care_summary):
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">📊 核心指标概览</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric('照护记录数', f'{care_summary.get("total_records", 0)} 条')
    with c2:
        st.metric('照护人数量', f'{care_summary.get("unique_caregivers", 0)} 人')
    with c3:
        st.metric('平均流程完成率', f'{care_summary.get("avg_routine_rate", 0)}%')
    with c4:
        score = consistency.get('overall', 0)
        level = consistency.get('level', '数据不足')
        st.metric('一致性评分', f'{score} 分', delta=level, delta_color='normal' if score >= 60 else 'inverse')

    st.markdown('---')
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">🎯 一致性评分详情</div>', unsafe_allow_html=True)

    col_gauge, col_radar = st.columns([1, 1])
    with col_gauge:
        st.plotly_chart(plot_consistency_gauge(consistency), use_container_width=True)
    with col_radar:
        st.plotly_chart(plot_consistency_radar(consistency), use_container_width=True)

    st.markdown('---')
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">🛌 睡前流程完成率</div>', unsafe_allow_html=True)

    cg_routine = routine_result.get('by_caregiver', {})
    if cg_routine:
        cols = st.columns(min(len(cg_routine), 4))
        for i, (cg, info) in enumerate(cg_routine.items()):
            with cols[i % len(cols)]:
                rate = info.get('avg_rate', 0)
                delta_color = 'normal' if rate >= 60 else 'inverse'
                st.metric(f'{cg}', f'{rate}%', delta=f'记录{info.get("count", 0)}条', delta_color='off')

    item_freq = routine_result.get('item_frequency', {})
    if item_freq:
        st.plotly_chart(plot_routine_items_frequency(item_freq), use_container_width=True)

    st.markdown('---')
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">🌙 照护人夜醒响应差异</div>', unsafe_allow_html=True)

    by_cg = nw_diff_result.get('by_caregiver', {})
    if by_cg:
        cols = st.columns(min(len(by_cg), 4))
        for i, (cg, info) in enumerate(by_cg.items()):
            with cols[i % len(cols)]:
                nw_val = info.get('avg_nightwakings', '-')
                st.metric(f'{cg}', f'{nw_val} 次夜醒', delta=f'主响应: {info.get("primary_response", "")}', delta_color='off')

    for alert in nw_diff_result.get('difference_alerts', []):
        alert_class = 'care-alert-warning' if alert['type'] == 'warning' else 'care-alert-info'
        st.markdown(f"""
        <div class="{alert_class}">
            <div style="font-weight:600">{alert['title']}</div>
            <div style="font-size:0.9em;margin-top:4px">{alert['detail']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('---')
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">📋 干预计划执行偏差</div>', unsafe_allow_html=True)

    dev_score = deviation_result.get('deviation_score', 0)
    if dev_score >= 70:
        st.success(f'✅ 干预计划执行一致性：{dev_score} 分 — 执行较好')
    elif dev_score >= 50:
        st.warning(f'⚠️ 干预计划执行一致性：{dev_score} 分 — 存在偏差')
    else:
        st.error(f'🔴 干预计划执行一致性：{dev_score} 分 — 偏差较大')

    for alert in deviation_result.get('alerts', []):
        alert_class = 'care-alert-warning' if alert['type'] == 'warning' else 'care-alert-info'
        st.markdown(f"""
        <div class="{alert_class}">
            <div style="font-weight:600">{alert['title']}</div>
            <div style="font-size:0.9em;margin-top:4px">{alert['detail']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('---')
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">🔍 自动识别模式</div>', unsafe_allow_html=True)

    type_map = {
        'warning': ('care-alert-warning', '⚠️ 风险信号'),
        'info': ('care-alert-info', 'ℹ️ 观察提示'),
        'success': ('care-alert-success', '✅ 良好表现'),
    }
    for p in patterns:
        cls, label = type_map.get(p['type'], ('care-alert-info', p['type']))
        st.markdown(f"""
        <div class="{cls}">
            <div style="font-weight:600">{label}：{p['title']}</div>
            <div style="font-size:0.95rem;margin-top:4px">{p['detail']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('---')
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">🔗 照护记录与睡眠数据联动</div>', unsafe_allow_html=True)

    if 'sleep_nw' in care_df.columns:
        st.plotly_chart(plot_caregiver_sleep_correlation(care_df), use_container_width=True)

        env_change_df = care_df[care_df['env_change'] != '无']
        no_env_df = care_df[care_df['env_change'] == '无']
        if len(env_change_df) >= 1 and len(no_env_df) >= 1:
            env_nw = env_change_df['sleep_nw'].mean()
            no_env_nw = no_env_df['sleep_nw'].mean()
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.metric('环境变动日平均夜醒', f'{env_nw:.1f} 次')
            with col_e2:
                st.metric('无变动日平均夜醒', f'{no_env_nw:.1f} 次')

        event_df = care_df[care_df['temp_event'].str.strip() != '']
        if len(event_df) >= 1:
            event_nw = event_df['sleep_nw'].mean()
            st.info(f'📋 有临时事件记录的日子共 {len(event_df)} 天，平均夜醒 {event_nw:.1f} 次')


def _render_charts(care_df, timeline, routine_result, nw_diff_result, consistency, deviation_result):
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">📈 交接时间线</div>', unsafe_allow_html=True)
    st.plotly_chart(plot_handover_timeline(timeline, care_df), use_container_width=True)

    st.markdown('---')
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">🛌 睡前流程完成率</div>', unsafe_allow_html=True)
    st.plotly_chart(plot_routine_completion(care_df), use_container_width=True)

    st.markdown('---')
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">🌙 照护人差异分析</div>', unsafe_allow_html=True)
    st.plotly_chart(plot_nw_response_diff(nw_diff_result), use_container_width=True)

    st.markdown('---')
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">📋 干预执行偏差</div>', unsafe_allow_html=True)
    st.plotly_chart(plot_intervention_deviation(deviation_result, care_df), use_container_width=True)


def _render_export(care_df, consistency, routine_result, nw_diff_result, deviation_result, patterns, care_summary, filter_age, filter_feeding, filter_teething, filter_weather, date_range, exclude_anomalies):
    st.markdown('<div style="font-size:1.1rem;font-weight:600;color:#374151;padding:0.5rem 0;margin-bottom:0.8rem;border-bottom:2px solid #E5E7EB">📄 照护协同交接报告</div>', unsafe_allow_html=True)
    st.caption('导出完整 Excel 报告，包含照护记录明细、一致性评分、流程执行、差异分析、偏差对比、风险提醒与协同建议')

    if st.button('📥 生成并下载照护协同交接报告', type='primary', use_container_width=True, key='export_care'):
        with st.spinner('正在生成报告...'):
            filters_info = {
                '月龄阶段': filter_age,
                '喂养方式': filter_feeding,
                '是否长牙': filter_teething,
                '天气': filter_weather,
                '日期范围': f'{date_range[0]} ~ {date_range[1]}' if date_range and len(date_range) == 2 else ('全部' if not date_range else str(date_range[0])),
                '排除异常记录': '是' if exclude_anomalies else '否',
                '照护人筛选': st.session_state.get('filter_caregiver', '全部'),
            }
            report_io = export_care_report_to_excel(
                care_df, consistency, routine_result, nw_diff_result,
                deviation_result, patterns, care_summary, filters_info
            )
            st.success('✅ 报告生成成功！')
            st.download_button(
                label='⬇️ 下载照护协同交接报告 (.xlsx)',
                data=report_io,
                file_name=f'照护协同交接报告_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True,
            )

    with st.expander('👀 预览报告包含内容'):
        st.markdown("""
        **Sheet 1：照护记录明细**
        - 每日照护人、睡前流程、完成率、安抚方式、夜醒响应、环境变动、临时事件、交接备注

        **Sheet 2：交接一致性评分**
        - 综合评分、睡前流程一致性、夜醒响应一致性、交接充分性
        - 筛选条件说明

        **Sheet 3：睡前流程执行情况**
        - 总体完成率、各照护人完成率对比、各项目执行频率

        **Sheet 4：照护人差异分析**
        - 各照护人核心指标、夜醒响应方式分布、安抚策略差异

        **Sheet 5：干预偏差对比**
        - 执行一致性评分、逐日执行检查明细

        **Sheet 6：风险提醒与建议**
        - 自动识别模式、照护人差异提醒、干预偏差提醒、下一步协同建议
        """)
