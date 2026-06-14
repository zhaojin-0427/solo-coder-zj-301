import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from data_processor import minutes_to_time_display
from analyzer import age_based_sleep_norms


plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False


COLOR_PALETTE = {
    'primary': '#6366F1',
    'secondary': '#EC4899',
    'success': '#10B981',
    'warning': '#F59E0B',
    'danger': '#EF4444',
    'info': '#3B82F6',
    'sleep_night': '#6366F1',
    'sleep_nap': '#EC4899',
    'sleep_total': '#8B5CF6',
}


def plot_sleep_trend(df):
    if len(df) == 0:
        return go.Figure()
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('睡眠时长趋势', '夜醒频率趋势'),
        vertical_spacing=0.12,
        shared_xaxes=True
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['date'], y=df['night_sleep_hours'],
            name='夜间睡眠', mode='lines+markers',
            line=dict(color=COLOR_PALETTE['sleep_night'], width=2),
            marker=dict(size=6)
        ), row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df['date'], y=df['nap_hours'],
            name='白天小睡', mode='lines+markers',
            line=dict(color=COLOR_PALETTE['sleep_nap'], width=2),
            marker=dict(size=6)
        ), row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df['date'], y=df['total_sleep_hours'],
            name='总睡眠', mode='lines+markers',
            line=dict(color=COLOR_PALETTE['sleep_total'], width=2.5, dash='dash'),
            marker=dict(size=6)
        ), row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df['date'], y=df['nightwakings'],
            name='夜醒次数',
            marker_color=COLOR_PALETTE['danger'],
            opacity=0.75
        ), row=2, col=1
    )
    
    if 'nightwakings_7d_avg' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'], y=df['nightwakings_7d_avg'],
                name='7日平均夜醒', mode='lines',
                line=dict(color=COLOR_PALETTE['warning'], width=2)
            ), row=2, col=1
        )
    
    fig.update_yaxes(title_text='小时', row=1, col=1)
    fig.update_yaxes(title_text='次数', row=2, col=1)
    fig.update_layout(
        height=520,
        template='plotly_white',
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    return fig


def plot_nightwaking_heatmap(df):
    if len(df) == 0:
        return go.Figure()
    
    heatmap_data = []
    periods_order = ['入睡后(22-01)', '深夜(01-04)', '凌晨(04-06)', '清晨(06+)', '无夜醒']
    
    period_counts = df.groupby(['date', 'nw_period_group']).size().reset_index(name='count')
    
    pivot = period_counts.pivot(index='date', columns='nw_period_group', values='count').fillna(0)
    for p in periods_order:
        if p not in pivot.columns:
            pivot[p] = 0
    pivot = pivot[periods_order]
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values.T,
        x=[d.strftime('%m-%d') for d in pivot.index],
        y=periods_order,
        colorscale=[
            [0.0, '#F3F4F6'],
            [0.25, '#FEF3C7'],
            [0.5, '#FCD34D'],
            [0.75, '#F97316'],
            [1.0, '#DC2626']
        ],
        showscale=True,
        colorbar=dict(title='发生天数'),
        hovertemplate='日期: %{x}<br>时段: %{y}<br>次数: %{z}<extra></extra>'
    ))
    
    fig.update_layout(
        title='夜醒时段分布热力图',
        height=320,
        template='plotly_white',
        yaxis=dict(autorange='reversed')
    )
    return fig


def plot_naps_distribution(df):
    if len(df) == 0:
        return go.Figure()
    
    nap_stats = df.groupby('naps_group').agg({
        'nightwakings': 'mean',
        'total_sleep_hours': 'mean',
        'date': 'count'
    }).reset_index()
    nap_stats.columns = ['小睡次数', '平均夜醒', '平均总睡眠', '天数']
    
    order = ['1次及以下', '2次', '3次', '4次及以上', '未知']
    nap_stats['小睡次数'] = pd.Categorical(nap_stats['小睡次数'], categories=order, ordered=True)
    nap_stats = nap_stats.sort_values('小睡次数')
    nap_stats = nap_stats[nap_stats['小睡次数'] != '未知']
    
    if len(nap_stats) == 0:
        return go.Figure()
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('不同小睡次数的夜醒对比', '小睡时长与总睡眠关系'),
        column_widths=[0.5, 0.5]
    )
    
    colors = [COLOR_PALETTE['info'], COLOR_PALETTE['primary'], 
              COLOR_PALETTE['secondary'], COLOR_PALETTE['warning']]
    fig.add_trace(
        go.Bar(
            x=nap_stats['小睡次数'],
            y=nap_stats['平均夜醒'],
            marker_color=colors[:len(nap_stats)],
            text=nap_stats['平均夜醒'].round(1),
            textposition='outside',
            name='平均夜醒次数'
        ), row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['total_nap_minutes'].dropna() / 60,
            y=df['night_sleep_hours'].dropna(),
            mode='markers',
            marker=dict(
                size=8,
                color=df['nightwakings'].dropna(),
                colorscale='RdYlGn_r',
                showscale=True,
                colorbar=dict(title='夜醒次数', x=1.1)
            ),
            text=df['date'].dt.strftime('%Y-%m-%d'),
            hovertemplate='%{text}<br>小睡: %{x:.1f}h<br>夜间: %{y:.1f}h',
            name='每日数据'
        ), row=1, col=2
    )
    
    fig.update_yaxes(title_text='平均夜醒次数', row=1, col=1)
    fig.update_xaxes(title_text='白天小睡次数', row=1, col=1)
    fig.update_xaxes(title_text='白天小睡时长(小时)', row=1, col=2)
    fig.update_yaxes(title_text='夜间睡眠时长(小时)', row=1, col=2)
    
    fig.update_layout(
        height=360,
        template='plotly_white',
        showlegend=False
    )
    return fig


def plot_stability_gauge(score_data):
    fig = go.Figure()
    
    overall = score_data.get('overall', 50)
    
    fig.add_trace(go.Indicator(
        mode='gauge+number+delta',
        value=overall,
        title={'text': f"作息稳定度<br><span style='font-size:0.7em;color:gray'>{score_data.get('level', '')}</span>"},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': 'darkgray'},
            'bar': {'color': COLOR_PALETTE['primary'] if overall >= 60 else 
                    COLOR_PALETTE['warning'] if overall >= 40 else COLOR_PALETTE['danger']},
            'bgcolor': 'white',
            'borderwidth': 2,
            'bordercolor': 'lightgray',
            'steps': [
                {'range': [0, 40], 'color': '#FEE2E2'},
                {'range': [40, 60], 'color': '#FEF3C7'},
                {'range': [60, 80], 'color': '#DBEAFE'},
                {'range': [80, 100], 'color': '#D1FAE5'}
            ],
            'threshold': {
                'line': {'color': 'red', 'width': 4},
                'thickness': 0.75,
                'value': overall
            }
        }
    ))
    
    fig.update_layout(
        height=280,
        template='plotly_white',
        margin=dict(l=30, r=30, t=60, b=30)
    )
    return fig


def plot_stability_radar(score_data):
    categories = ['入睡时间稳定', '起床时间稳定', '小睡稳定']
    values = [
        score_data.get('bedtime_stability', 50),
        score_data.get('wakeup_stability', 50),
        score_data.get('nap_stability', 50)
    ]
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor=f'rgba(99, 102, 241, 0.3)',
        line=dict(color=COLOR_PALETTE['primary'], width=2),
        marker=dict(size=8, color=COLOR_PALETTE['primary'])
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[20, 40, 60, 80, 100]
            )
        ),
        showlegend=False,
        height=300,
        margin=dict(l=40, r=40, t=20, b=20)
    )
    return fig


def plot_bedtime_vs_wakings(df):
    if len(df) < 5:
        return go.Figure()
    
    valid = df.dropna(subset=['bedtime_minutes', 'nightwakings']).copy()
    if len(valid) < 5:
        return go.Figure()
    
    valid['日期'] = valid['date'].dt.strftime('%Y-%m-%d')
    valid['入睡时间显示'] = valid['bedtime_minutes'].apply(minutes_to_time_display)
    valid['夜间睡眠(h)'] = valid['night_sleep_hours'].round(1)
    valid['夜醒次数显示'] = valid['nightwakings']
    valid['夜眠大小'] = valid['night_sleep_hours'].fillna(6)
    
    fig = px.scatter(
        valid,
        x='bedtime_minutes',
        y='nightwakings',
        size='夜眠大小',
        color='age_group',
        hover_data={'日期': True,
                    '入睡时间显示': True,
                    '夜醒次数显示': True,
                    '夜间睡眠(h)': True,
                    'bedtime_minutes': False,
                    'nightwakings': False,
                    '夜眠大小': False},
        trendline='ols',
        trendline_color_override='red',
        title='入睡时间与夜醒关系',
        labels={'bedtime_minutes': '入睡时间 (负值为20点后，正值为凌晨)',
                'nightwakings': '夜醒次数'}
    )
    
    x_ticks = [-240, -180, -120, -60, 0, 60, 120, 180]
    x_labels = ['20:00', '21:00', '22:00', '23:00', '00:00', '01:00', '02:00', '03:00']
    
    fig.update_layout(
        height=360,
        template='plotly_white',
        xaxis=dict(tickvals=x_ticks, ticktext=x_labels),
        legend_title='月龄阶段'
    )
    return fig


def plot_milk_analysis(df):
    if len(df) == 0 or df['milk_amount_ml'].notna().sum() < 5:
        return go.Figure()
    
    milk_stats = df.groupby('milk_group').agg({
        'nightwakings': 'mean',
        'total_sleep_hours': 'mean',
        'date': 'count'
    }).reset_index()
    milk_stats.columns = ['奶量区间', '平均夜醒', '平均总睡眠', '天数']
    milk_stats = milk_stats[milk_stats['奶量区间'] != '未知']
    
    order = ['500ml以下', '500-699ml', '700-899ml', '900ml以上']
    milk_stats['奶量区间'] = pd.Categorical(milk_stats['奶量区间'], categories=order, ordered=True)
    milk_stats = milk_stats.sort_values('奶量区间')
    
    if len(milk_stats) < 2:
        return go.Figure()
    
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    
    fig.add_trace(
        go.Bar(
            x=milk_stats['奶量区间'],
            y=milk_stats['平均夜醒'],
            name='平均夜醒次数',
            marker_color=COLOR_PALETTE['danger'],
            opacity=0.8,
            text=milk_stats['平均夜醒'].round(1),
            textposition='outside'
        ), secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=milk_stats['奶量区间'],
            y=milk_stats['平均总睡眠'],
            name='平均总睡眠(小时)',
            mode='lines+markers',
            line=dict(color=COLOR_PALETTE['primary'], width=3),
            marker=dict(size=10)
        ), secondary_y=True
    )
    
    fig.update_layout(
        title='奶量区间与睡眠质量分析',
        height=340,
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    fig.update_yaxes(title_text='平均夜醒次数', secondary_y=False)
    fig.update_yaxes(title_text='总睡眠(小时)', secondary_y=True)
    return fig


def plot_age_comparison(df):
    if len(df) == 0:
        return go.Figure()
    
    age_groups = df['age_group'].value_counts()
    age_groups = age_groups[age_groups >= 3]
    if len(age_groups) < 1:
        return go.Figure()
    
    filtered = df[df['age_group'].isin(age_groups.index)]
    age_stats = filtered.groupby('age_group').agg({
        'total_sleep_hours': ['mean', 'std'],
        'nightwakings': 'mean',
        'naps_count': 'mean'
    }).round(2)
    age_stats.columns = ['总睡眠_avg', '总睡眠_std', '夜醒_avg', '小睡_avg']
    age_stats = age_stats.reset_index()
    
    norms = age_based_sleep_norms()
    norm_mid = []
    for ag in age_stats['age_group']:
        if ag in norms:
            n = norms[ag]
            norm_mid.append((n['total'][0] + n['total'][1]) / 2)
        else:
            norm_mid.append(None)
    age_stats['推荐总睡眠'] = norm_mid
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=age_stats['age_group'],
        y=age_stats['总睡眠_avg'],
        name='实际总睡眠',
        marker_color=COLOR_PALETTE['primary'],
        error_y=dict(type='data', array=age_stats['总睡眠_std'], visible=True),
        text=age_stats['总睡眠_avg'].round(1),
        textposition='outside'
    ))
    
    if age_stats['推荐总睡眠'].notna().any():
        fig.add_trace(go.Scatter(
            x=age_stats['age_group'],
            y=age_stats['推荐总睡眠'],
            name='推荐范围中值',
            mode='markers',
            marker=dict(symbol='star', size=18, color=COLOR_PALETTE['warning']),
            text=age_stats['推荐总睡眠'].round(1)
        ))
    
    fig.update_layout(
        title='各月龄阶段睡眠对比（含误差棒）',
        height=360,
        template='plotly_white',
        barmode='group',
        yaxis_title='小时',
        xaxis_title='月龄阶段'
    )
    return fig


def plot_weekly_pattern(df):
    if len(df) < 7:
        return go.Figure()
    
    df_cp = df.copy()
    df_cp['weekday'] = df_cp['date'].dt.day_name()
    weekday_map = {'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三', 
                   'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'}
    df_cp['weekday'] = df_cp['weekday'].map(weekday_map)
    
    day_order = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    weekly = df_cp.groupby('weekday').agg({
        'nightwakings': 'mean',
        'total_sleep_hours': 'mean',
        'bedtime_minutes': 'mean'
    }).round(2).reindex(day_order).reset_index()
    weekly = weekly.dropna()
    
    if len(weekly) < 3:
        return go.Figure()
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('周内夜醒频率变化', '周内总睡眠时长变化'),
        vertical_spacing=0.15,
        shared_xaxes=True
    )
    
    fig.add_trace(
        go.Bar(
            x=weekly['weekday'],
            y=weekly['nightwakings'],
            name='平均夜醒',
            marker_color=COLOR_PALETTE['danger'],
            text=weekly['nightwakings'].round(1),
            textposition='outside'
        ), row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=weekly['weekday'],
            y=weekly['total_sleep_hours'],
            name='平均总睡眠',
            mode='lines+markers',
            line=dict(color=COLOR_PALETTE['primary'], width=3),
            marker=dict(size=10)
        ), row=2, col=1
    )
    
    fig.update_yaxes(title_text='夜醒次数', row=1, col=1)
    fig.update_yaxes(title_text='小时', row=2, col=1)
    fig.update_layout(
        height=420,
        template='plotly_white',
        showlegend=False
    )
    return fig
