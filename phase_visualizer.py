import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from data_processor import minutes_to_time_display

COLOR_PALETTE = {
    'primary': '#6366F1',
    'secondary': '#EC4899',
    'success': '#10B981',
    'warning': '#F59E0B',
    'danger': '#EF4444',
    'info': '#3B82F6',
    'phase1': '#6366F1',
    'phase2': '#10B981',
    'phase3': '#F59E0B',
    'phase4': '#EC4899',
    'phase5': '#8B5CF6',
    'phase6': '#06B6D4',
}


def get_phase_color(index):
    keys = list(COLOR_PALETTE.keys())
    phase_keys = [k for k in keys if k.startswith('phase')]
    return COLOR_PALETTE[phase_keys[index % len(phase_keys)]]


def plot_phase_metrics_comparison(phase_results):
    if len(phase_results) < 1:
        return go.Figure()
    
    phase_names = [pr['phase_name'] for pr in phase_results]
    metrics_to_show = [
        ('avg_total_sleep_hours', '总睡眠(小时/天)'),
        ('avg_night_sleep_hours', '夜间睡眠(小时)'),
        ('avg_nap_hours', '白天小睡(小时)'),
        ('avg_nightwakings', '夜醒次数(次/夜)'),
    ]
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[m[1] for m in metrics_to_show],
        vertical_spacing=0.2,
        horizontal_spacing=0.12
    )
    
    for i, (metric_key, metric_label) in enumerate(metrics_to_show):
        row = (i // 2) + 1
        col = (i % 2) + 1
        values = []
        for pr in phase_results:
            v = pr['metrics'].get(metric_key, 0)
            values.append(round(v, 2) if v is not None else 0)
        
        colors = [get_phase_color(i) for i in range(len(phase_results))]
        
        fig.add_trace(
            go.Bar(
                x=phase_names,
                y=values,
                name=metric_label,
                marker_color=colors,
                text=[str(v) for v in values],
                textposition='outside',
                showlegend=False
            ),
            row=row, col=col
        )
    
    fig.update_layout(
        height=560,
        template='plotly_white',
        title='各阶段核心指标对比',
        barmode='group'
    )
    return fig


def plot_phase_trend_comparison(df_phases_dict, phase_names):
    if len(df_phases_dict) < 1:
        return go.Figure()
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('各阶段睡眠时长趋势对比', '各阶段夜醒趋势对比'),
        vertical_spacing=0.12,
        shared_xaxes=False
    )
    
    for i, (phase_name, df_phase) in enumerate(df_phases_dict.items()):
        if len(df_phase) == 0:
            continue
        color = get_phase_color(i)
        
        x_vals = list(range(1, len(df_phase) + 1))
        
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=df_phase['total_sleep_hours'].values,
                name=f'{phase_name} - 总睡眠',
                mode='lines+markers',
                line=dict(color=color, width=2),
                marker=dict(size=5),
                opacity=0.85
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=x_vals,
                y=df_phase['nightwakings'].values,
                name=f'{phase_name} - 夜醒',
                mode='lines+markers',
                line=dict(color=color, width=2, dash='dash'),
                marker=dict(size=5),
                opacity=0.85
            ),
            row=2, col=1
        )
    
    fig.update_yaxes(title_text='小时', row=1, col=1)
    fig.update_yaxes(title_text='次数', row=2, col=1)
    fig.update_xaxes(title_text='阶段内天数', row=1, col=1)
    fig.update_xaxes(title_text='阶段内天数', row=2, col=1)
    
    fig.update_layout(
        height=520,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    return fig


def plot_phase_nw_periods_comparison(phase_results):
    if len(phase_results) < 1:
        return go.Figure()
    
    periods_order = ['入睡后(22-01)', '深夜(01-04)', '凌晨(04-06)', '清晨(06+)']
    phase_names = [pr['phase_name'] for pr in phase_results]
    
    data_matrix = []
    for pr in phase_results:
        dist = pr.get('nw_period_distribution', {})
        row = []
        total = sum(dist.values()) or 1
        for p in periods_order:
            row.append(round(dist.get(p, 0) / total * 100, 1))
        data_matrix.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=data_matrix,
        x=periods_order,
        y=phase_names,
        colorscale=[
            [0.0, '#F3F4F6'],
            [0.25, '#DBEAFE'],
            [0.5, '#93C5FD'],
            [0.75, '#3B82F6'],
            [1.0, '#1D4ED8']
        ],
        showscale=True,
        colorbar=dict(title='占比(%)'),
        text=[[f'{v}%' for v in row] for row in data_matrix],
        texttemplate='%{text}',
        hovertemplate='阶段: %{y}<br>时段: %{x}<br>占比: %{z}%<extra></extra>'
    ))
    
    fig.update_layout(
        title='各阶段夜醒时段分布对比（占比）',
        height=120 + len(phase_names) * 60,
        template='plotly_white',
        yaxis=dict(autorange='reversed')
    )
    return fig


def plot_phase_radar(phase_results):
    if len(phase_results) < 1:
        return go.Figure()
    
    categories = [
        '总睡眠',
        '夜间睡眠',
        '夜醒改善',
        '作息稳定度',
        '入睡窗口稳定',
        '小睡充足度'
    ]
    
    fig = go.Figure()
    
    all_values = []
    for pr in phase_results:
        m = pr['metrics']
        total_sleep = min(100, (m.get('avg_total_sleep_hours', 0) / 14) * 100)
        night_sleep = min(100, (m.get('avg_night_sleep_hours', 0) / 12) * 100)
        nw_score = max(0, 100 - m.get('avg_nightwakings', 0) * 25)
        stab_score = pr['stability'].get('overall', 0)
        bt_stab = m.get('bedtime_window_stability', 0)
        nap_score = min(100, (m.get('avg_nap_hours', 0) / 5) * 100)
        
        values = [total_sleep, night_sleep, nw_score, stab_score, bt_stab, nap_score]
        all_values.append(values)
    
    for i, pr in enumerate(phase_results):
        color = get_phase_color(i)
        values = all_values[i] + [all_values[i][0]]
        cats = categories + [categories[0]]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=cats,
            fill='toself',
            name=pr['phase_name'],
            fillcolor=f'rgba{tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (0.2,)}',
            line=dict(color=color, width=2),
            marker=dict(size=6, color=color)
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[20, 40, 60, 80, 100]
            )
        ),
        showlegend=True,
        height=440,
        template='plotly_white',
        title='各阶段综合睡眠质量雷达图'
    )
    return fig


def plot_milk_nw_correlation_comparison(phase_results):
    valid_phases = []
    correlations = []
    for pr in phase_results:
        corr = pr.get('milk_nw_correlation')
        if corr is not None:
            valid_phases.append(pr['phase_name'])
            correlations.append(corr)
    
    if not valid_phases:
        fig = go.Figure()
        fig.update_layout(
            title='奶量与夜醒相关性对比',
            height=300,
            template='plotly_white',
            annotations=[dict(text='暂无足够数据（每阶段需≥5天有奶量记录）',
                              x=0.5, y=0.5, showarrow=False,
                              font=dict(size=14, color='#9CA3AF'))]
        )
        return fig
    
    colors = [get_phase_color(i) for i in range(len(valid_phases))]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=valid_phases,
        y=correlations,
        marker_color=colors,
        text=[f'{c:.3f}' for c in correlations],
        textposition='outside'
    ))
    
    fig.add_hline(y=0, line_dash='dash', line_color='gray')
    
    fig.update_layout(
        title='奶量与夜醒次数相关性对比',
        height=360,
        template='plotly_white',
        yaxis_title='相关系数（负值=奶量越多夜醒越少）',
        yaxis=dict(range=[-1, 1])
    )
    return fig


def plot_prediction_vs_actual(comparison_result):
    if not comparison_result:
        return go.Figure()
    
    metrics = [
        ('nightwakings', '夜醒次数(次/夜)', 'inverse'),
        ('total_sleep_hours', '总睡眠时长(小时/天)', 'normal'),
        ('stability_score', '作息稳定度(分)', 'normal'),
    ]
    
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=[m[1] for m in metrics],
        column_widths=[0.33, 0.33, 0.34]
    )
    
    for i, (metric_key, metric_label, mode) in enumerate(metrics):
        data = comparison_result.get(metric_key, {})
        if not data:
            continue
        
        categories = ['基线', '预测', '实际']
        values = [
            data.get('baseline', 0),
            data.get('predicted', 0),
            data.get('actual', 0)
        ]
        colors = [COLOR_PALETTE['info'], COLOR_PALETTE['warning'], COLOR_PALETTE['success']]
        
        fig.add_trace(
            go.Bar(
                x=categories,
                y=values,
                marker_color=colors,
                text=[f'{v:.2f}' for v in values],
                textposition='outside',
                showlegend=False
            ),
            row=1, col=i + 1
        )
    
    fig.update_layout(
        height=380,
        template='plotly_white',
        title='干预效果：预测值 vs 实际值'
    )
    return fig


def plot_phase_status_timeline(phase_results):
    if len(phase_results) < 1:
        return go.Figure()
    
    status_colors = {
        '改善中': '#10B981',
        '改善中（稳定性待提升）': '#34D399',
        '稳定良好': '#059669',
        '反复波动': '#F59E0B',
        '观察中': '#6B7280',
        '不稳定': '#F97316',
        '阶段倒退': '#EF4444',
        '数据不足': '#9CA3AF',
    }
    
    phase_names = [pr['phase_name'] for pr in phase_results]
    statuses = [pr.get('status', '数据不足') for pr in phase_results]
    colors = [status_colors.get(s, '#9CA3AF') for s in statuses]
    days = [pr.get('days_count', 0) for pr in phase_results]
    
    fig = go.Figure()
    
    for i, (name, status, color, day_count) in enumerate(zip(phase_names, statuses, colors, days)):
        fig.add_trace(go.Bar(
            x=[name],
            y=[1],
            marker_color=color,
            text=[f'{status}<br>({day_count}天)'],
            textposition='inside',
            insidetextanchor='middle',
            showlegend=False,
            hovertemplate=f'阶段: {name}<br>状态: {status}<br>天数: {day_count}<extra></extra>'
        ))
    
    for status, color in status_colors.items():
        if status in statuses:
            fig.add_trace(go.Bar(
                x=[None], y=[None],
                marker_color=color,
                name=status,
                showlegend=True
            ))
    
    fig.update_layout(
        title='各阶段状态时间轴',
        height=240,
        template='plotly_white',
        barmode='stack',
        yaxis=dict(visible=False),
        xaxis=dict(visible=False),
        legend=dict(orientation='h', yanchor='bottom', y=-0.3, xanchor='center', x=0.5)
    )
    return fig
