import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

CARE_COLORS = {
    '妈妈': '#EC4899',
    '爸爸': '#3B82F6',
    '老人': '#F59E0B',
    '保姆': '#10B981',
    '未指定': '#9CA3AF',
}


def _get_color(caregiver):
    return CARE_COLORS.get(caregiver, '#6B7280')


def plot_handover_timeline(timeline, care_df=None):
    if not timeline:
        return go.Figure()
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('照护人交接时间线', '每日照护人数与交接详情'),
        vertical_spacing=0.15,
        row_heights=[0.6, 0.4]
    )
    dates = [t['date'] for t in timeline]
    for cg in CARE_COLORS.keys():
        y_vals = []
        for t in timeline:
            y_vals.append(1 if cg in t['caregivers'] else 0)
        fig.add_trace(
            go.Bar(
                x=dates, y=y_vals,
                name=cg,
                marker_color=_get_color(cg),
                opacity=0.8,
                showlegend=True,
            ), row=1, col=1
        )
    cg_counts = [t['caregiver_count'] for t in timeline]
    fig.add_trace(
        go.Scatter(
            x=dates, y=cg_counts,
            name='照护人数',
            mode='lines+markers',
            line=dict(color='#6366F1', width=2),
            marker=dict(size=8),
        ), row=2, col=1
    )
    has_notes = []
    if care_df is not None and 'handover_note' in care_df.columns:
        for t in timeline:
            day_df = care_df[care_df['date'] == t['date']]
            note_count = (day_df['handover_note'].str.strip() != '').sum()
            has_notes.append(note_count)
        fig.add_trace(
            go.Bar(
                x=dates, y=has_notes,
                name='交接备注数',
                marker_color='#8B5CF6',
                opacity=0.6,
            ), row=2, col=1
        )
    fig.update_layout(
        height=550,
        barmode='stack',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=50, r=30, t=80, b=50),
    )
    fig.update_yaxes(title_text='照护人参与', row=1, col=1)
    fig.update_yaxes(title_text='人数/备注数', row=2, col=1)
    return fig


def plot_routine_completion(care_df):
    if care_df is None or len(care_df) == 0 or 'routine_completion_rate' not in care_df.columns:
        return go.Figure()
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('各照护人睡前流程完成率', '每日睡前流程完成率趋势'),
        column_widths=[0.4, 0.6]
    )
    cg_stats = care_df.groupby('caregiver')['routine_completion_rate'].agg(['mean', 'min', 'max']).reset_index()
    for _, row in cg_stats.iterrows():
        fig.add_trace(
            go.Bar(
                y=[row['caregiver']],
                x=[row['mean']],
                orientation='h',
                name=row['caregiver'],
                marker_color=_get_color(row['caregiver']),
                error_x=dict(type='data', symmetric=False, array=[row['max'] - row['mean']], arrayminus=[row['mean'] - row['min']]),
                showlegend=False,
            ), row=1, col=1
        )
    daily_avg = care_df.groupby('date')['routine_completion_rate'].mean().reset_index()
    daily_avg.columns = ['date', 'avg_rate']
    fig.add_trace(
        go.Scatter(
            x=daily_avg['date'],
            y=daily_avg['avg_rate'],
            mode='lines+markers',
            name='平均完成率',
            line=dict(color='#6366F1', width=2),
            marker=dict(size=6),
        ), row=1, col=2
    )
    fig.add_hline(y=60, line_dash='dash', line_color='#EF4444', annotation_text='60%基准线', row=1, col=2)
    for cg in care_df['caregiver'].unique():
        cg_daily = care_df[care_df['caregiver'] == cg].groupby('date')['routine_completion_rate'].mean().reset_index()
        fig.add_trace(
            go.Scatter(
                x=cg_daily['date'],
                y=cg_daily['routine_completion_rate'],
                mode='lines',
                name=cg,
                line=dict(color=_get_color(cg), width=1.5, dash='dot'),
            ), row=1, col=2
        )
    fig.update_layout(
        height=400,
        margin=dict(l=50, r=30, t=60, b=50),
    )
    fig.update_xaxes(title_text='完成率(%)', row=1, col=1)
    fig.update_xaxes(title_text='日期', row=1, col=2)
    fig.update_yaxes(title_text='完成率(%)', row=1, col=2)
    return fig


def plot_nw_response_diff(nw_diff_result):
    by_cg = nw_diff_result.get('by_caregiver', {})
    if not by_cg:
        return go.Figure()
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('各照护人平均夜醒次数', '夜醒响应方式分布'),
        column_widths=[0.4, 0.6]
    )
    caregivers = list(by_cg.keys())
    nw_vals = [by_cg[cg].get('avg_nightwakings', 0) or 0 for cg in caregivers]
    colors = [_get_color(cg) for cg in caregivers]
    fig.add_trace(
        go.Bar(
            x=caregivers,
            y=nw_vals,
            marker_color=colors,
            name='平均夜醒',
            showlegend=False,
        ), row=1, col=1
    )
    all_responses = set()
    for cg, info in by_cg.items():
        resp_dist = info.get('nw_response_distribution', {})
        all_responses.update(resp_dist.keys())
    all_responses = sorted(all_responses)
    for resp in all_responses:
        vals = [by_cg[cg].get('nw_response_distribution', {}).get(resp, 0) for cg in caregivers]
        fig.add_trace(
            go.Bar(
                x=caregivers,
                y=vals,
                name=resp,
            ), row=1, col=2
        )
    fig.update_layout(
        height=400,
        barmode='group',
        legend=dict(orientation='h', yanchor='bottom', y=1.08, xanchor='center', x=0.5, font=dict(size=9)),
        margin=dict(l=50, r=30, t=80, b=50),
    )
    fig.update_yaxes(title_text='夜醒次数', row=1, col=1)
    fig.update_yaxes(title_text='使用次数', row=1, col=2)
    return fig


def plot_consistency_gauge(consistency):
    score = consistency.get('overall', 0)
    if score >= 80:
        color = '#10B981'
    elif score >= 60:
        color = '#3B82F6'
    elif score >= 40:
        color = '#F59E0B'
    else:
        color = '#EF4444'
    fig = go.Figure(go.Indicator(
        mode='gauge+number+delta',
        value=score,
        domain=dict(x=[0, 1], y=[0, 1]),
        title=dict(text='照护一致性评分', font=dict(size=16)),
        delta=dict(reference=80, increasing=dict(color='#10B981'), decreasing=dict(color='#EF4444')),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor='#374151'),
            bar=dict(color=color, thickness=0.3),
            bgcolor='white',
            borderwidth=2,
            bordercolor='#E5E7EB',
            steps=[
                dict(range=[0, 40], color='#FEE2E2'),
                dict(range=[40, 60], color='#FEF3C7'),
                dict(range=[60, 80], color='#DBEAFE'),
                dict(range=[80, 100], color='#D1FAE5'),
            ],
            threshold=dict(line=dict(color='#374151', width=4), thickness=0.8, value=80),
        )
    ))
    fig.update_layout(height=280, margin=dict(l=30, r=30, t=60, b=20))
    return fig


def plot_consistency_radar(consistency):
    categories = ['睡前流程一致性', '夜醒响应一致性', '交接充分性']
    values = [
        consistency.get('routine_score', 0),
        consistency.get('response_score', 0),
        consistency.get('handover_score', 0),
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(99, 102, 241, 0.2)',
        line=dict(color='#6366F1', width=2),
        name='一致性得分',
    ))
    fig.add_trace(go.Scatterpolar(
        r=[80, 80, 80, 80],
        theta=categories + [categories[0]],
        line=dict(color='#10B981', width=1.5, dash='dash'),
        name='目标线(80分)',
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=350,
        margin=dict(l=30, r=30, t=30, b=30),
    )
    return fig


def plot_intervention_deviation(deviation_result, care_df):
    details = deviation_result.get('deviation_details', [])
    if not details:
        return go.Figure()
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('干预计划执行检查通过率', '各照护人执行偏差'),
        column_widths=[0.4, 0.6]
    )
    total = len(details)
    passed = sum(1 for d in details if all(d['checks'].values()))
    failed = total - passed
    pct_passed = round(passed / max(total, 1) * 100, 1)
    pct_failed = round(failed / max(total, 1) * 100, 1)
    fig.add_trace(
        go.Bar(
            y=['通过率'],
            x=[pct_passed],
            orientation='h',
            name='执行通过',
            marker_color='#10B981',
            text=[f'{pct_passed}% ({passed}条)'],
            textposition='inside',
            insidetextanchor='middle',
            showlegend=False,
        ), row=1, col=1
    )
    fig.add_trace(
        go.Bar(
            y=['通过率'],
            x=[pct_failed],
            orientation='h',
            name='存在偏差',
            marker_color='#EF4444',
            text=[f'{pct_failed}% ({failed}条)'],
            textposition='inside',
            insidetextanchor='middle',
            showlegend=False,
        ), row=1, col=1
    )
    if care_df is not None and len(care_df) > 0 and 'routine_completion_rate' in care_df.columns:
        cg_deviation = care_df.groupby('caregiver').agg(
            avg_rate=('routine_completion_rate', 'mean'),
            count=('routine_completion_rate', 'count')
        ).reset_index()
        fig.add_trace(
            go.Bar(
                x=cg_deviation['caregiver'],
                y=cg_deviation['avg_rate'],
                marker_color=[_get_color(cg) for cg in cg_deviation['caregiver']],
                name='平均完成率',
                showlegend=False,
            ), row=1, col=2
        )
        fig.add_hline(y=60, line_dash='dash', line_color='#EF4444', row=1, col=2)
    fig.update_layout(
        height=400,
        barmode='stack',
        margin=dict(l=50, r=30, t=60, b=50),
    )
    fig.update_xaxes(range=[0, 100], title_text='百分比(%)', row=1, col=1)
    return fig


def plot_routine_items_frequency(item_freq):
    if not item_freq:
        return go.Figure()
    items = sorted(item_freq.items(), key=lambda x: x[1], reverse=True)
    names = [x[0] for x in items]
    freqs = [x[1] for x in items]
    colors = ['#6366F1' if f >= 60 else '#F59E0B' if f >= 40 else '#EF4444' for f in freqs]
    fig = go.Figure(go.Bar(
        x=freqs,
        y=names,
        orientation='h',
        marker_color=colors,
    ))
    fig.add_vline(x=60, line_dash='dash', line_color='#10B981', annotation_text='60%基准')
    fig.update_layout(
        title='睡前流程各项目执行频率',
        height=400,
        margin=dict(l=120, r=30, t=60, b=50),
        xaxis_title='执行频率(%)',
    )
    return fig


def plot_caregiver_sleep_correlation(care_df):
    if care_df is None or len(care_df) == 0 or 'sleep_nw' not in care_df.columns:
        return go.Figure()
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('各照护人与夜醒关联', '各照护人与睡眠时长关联'),
    )
    cg_nw = care_df.groupby('caregiver')['sleep_nw'].mean().reset_index()
    fig.add_trace(
        go.Bar(
            x=cg_nw['caregiver'],
            y=cg_nw['sleep_nw'],
            marker_color=[_get_color(cg) for cg in cg_nw['caregiver']],
            name='平均夜醒',
            showlegend=False,
        ), row=1, col=1
    )
    if 'sleep_total_h' in care_df.columns:
        cg_sleep = care_df.groupby('caregiver')['sleep_total_h'].mean().reset_index()
        fig.add_trace(
            go.Bar(
                x=cg_sleep['caregiver'],
                y=cg_sleep['sleep_total_h'],
                marker_color=[_get_color(cg) for cg in cg_sleep['caregiver']],
                name='平均总睡眠',
                showlegend=False,
            ), row=1, col=2
        )
    fig.update_layout(
        height=380,
        margin=dict(l=50, r=30, t=60, b=50),
    )
    fig.update_yaxes(title_text='夜醒次数', row=1, col=1)
    fig.update_yaxes(title_text='总睡眠(小时)', row=1, col=2)
    return fig
