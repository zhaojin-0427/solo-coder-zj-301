import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processor import minutes_to_time_display
from intervention_params import SOOTHING_STRATEGY_LEVELS


def generate_daily_plan(baseline, params, prediction, priorities):
    days = params['sim_duration_days']
    plan_days = []
    
    bt_start = params['target_bedtime_start']
    bt_end = params['target_bedtime_end']
    bt_mid = (bt_start + bt_end) / 2
    
    last_nap_deadline = params['last_nap_deadline']
    nap_adj = params['nap_count_adjustment']
    milk_pct = params['milk_change_pct']
    strategy = params['soothing_strategy']
    
    base_naps = baseline['avg_naps_count']
    base_milk = baseline.get('avg_milk_ml', 0)
    
    for day in range(1, days + 1):
        progress = min(1.0, day / max(days * 0.6, 10))
        phase = _get_phase(day, days)
        
        daily_bt_mid = baseline['avg_bedtime_minutes'] + (bt_mid - baseline['avg_bedtime_minutes']) * progress
        daily_bt_start = daily_bt_mid - 30
        daily_bt_end = daily_bt_mid + 15
        
        daily_last_nap = baseline.get('avg_bedtime_minutes', 15*60) - 180 + (last_nap_deadline - (baseline.get('avg_bedtime_minutes', 15*60) - 180)) * progress
        
        daily_naps = base_naps + nap_adj * progress
        daily_milk = base_milk * (1 + milk_pct / 100 * progress) if base_milk else 0
        
        soothing_intensity = SOOTHING_STRATEGY_LEVELS[strategy]['intensity']
        if phase == '适应期':
            actual_soothing = max(1, soothing_intensity - 1)
        else:
            actual_soothing = soothing_intensity
        
        tips = _generate_daily_tips(day, phase, params, baseline, progress, priorities)
        
        plan_days.append({
            'day': day,
            'date': (datetime.now() + timedelta(days=day - 1)).strftime('%Y-%m-%d'),
            'weekday': (datetime.now() + timedelta(days=day - 1)).strftime('%A'),
            'phase': phase,
            'target_bedtime_window': f"{minutes_to_time_display(daily_bt_start)} ~ {minutes_to_time_display(daily_bt_end)}",
            'last_nap_deadline': minutes_to_time_display(daily_last_nap),
            'target_naps_count': round(daily_naps, 1),
            'target_milk_ml': round(daily_milk, 0) if daily_milk else 0,
            'soothing_level': _get_soothing_level_name(actual_soothing),
            'key_tasks': tips['key_tasks'],
            'note': tips['note'],
            'expected_nightwakings': round(prediction['predicted']['avg_nightwakings'] * (1 - (1 - day/days) * 0.5), 1),
        })
    
    return plan_days


def _get_phase(day, total_days):
    if day <= 3:
        return '适应期'
    elif day <= 7:
        return '调整期'
    elif day <= total_days * 0.7:
        return '巩固期'
    else:
        return '稳定期'


def _get_soothing_level_name(intensity):
    levels = {1: '轻柔安抚', 2: '适度安抚', 3: '渐进式训练'}
    return levels.get(intensity, '适度安抚')


def _generate_daily_tips(day, phase, params, baseline, progress, priorities):
    key_tasks = []
    note = ''
    
    if phase == '适应期':
        note = '适应期以建立固定流程为主，不追求立竿见影的效果，让宝宝逐步适应变化。'
        key_tasks.append('建立固定的睡前程序（洗澡-抚触-喂奶-故事）')
        key_tasks.append('记录准确的入睡和起床时间')
    elif phase == '调整期':
        note = '调整期开始逐步推进目标作息，观察宝宝反应，及时微调。'
        key_tasks.append('按照目标入睡窗口安排入睡')
        key_tasks.append('控制白天最后一觉结束时间')
        key_tasks.append('夜醒时采用预定安抚策略')
    elif phase == '巩固期':
        note = '巩固期持续执行干预方案，帮助宝宝形成稳定生物钟。'
        key_tasks.append('严格执行作息时间表')
        key_tasks.append('白天保证充足的活动量')
        key_tasks.append('睡前避免过度刺激')
    else:
        note = '稳定期重点是保持规律，可适当灵活但核心作息不变。'
        key_tasks.append('维持稳定的作息规律')
        key_tasks.append('定期评估睡眠质量')
    
    top_priority = priorities[0] if priorities else None
    if top_priority and day % 3 == 0:
        if top_priority['key'] == 'bedtime':
            key_tasks.append('重点关注：固定入睡时间，偏差不超过±30分钟')
        elif top_priority['key'] == 'last_nap':
            key_tasks.append('重点关注：确保最后一觉在规定时间前结束')
        elif top_priority['key'] == 'nap_count':
            key_tasks.append('重点关注：按计划调整白天小睡次数和时长')
        elif top_priority['key'] == 'milk':
            key_tasks.append('重点关注：保证白天奶量摄入，避免夜醒求奶')
        elif top_priority['key'] == 'soothing':
            key_tasks.append('重点关注：坚持执行夜醒安抚策略，不半途而废')
    
    if day == 7 or day == 14 or day == 21:
        key_tasks.append('周评估：回顾本周数据，调整下周计划')
    
    return {
        'key_tasks': key_tasks[:3],
        'note': note,
    }


def generate_intervention_calendar(plan_days):
    calendar_data = []
    
    for day_info in plan_days:
        calendar_data.append({
            '日期': day_info['date'],
            '天数': f"第 {day_info['day']} 天",
            '阶段': day_info['phase'],
            '入睡窗口': day_info['target_bedtime_window'],
            '最后一觉截止': day_info['last_nap_deadline'],
            '小睡目标': f"{day_info['target_naps_count']} 次",
            '奶量目标': f"{day_info['target_milk_ml']:.0f} ml" if day_info['target_milk_ml'] > 0 else '不变',
            '安抚策略': day_info['soothing_level'],
            '预计夜醒': f"{day_info['expected_nightwakings']:.1f} 次",
            '关键任务': '；'.join(day_info['key_tasks'][:2]),
        })
    
    return pd.DataFrame(calendar_data)


def generate_execution_summary(baseline, params, prediction, priorities, risks):
    summary = {
        'intervention_name': _generate_plan_name(params, priorities),
        'duration': f"{params['sim_duration_days']} 天",
        'phases': [
            {'name': '适应期', 'duration': '3天', 'focus': '建立睡前程序，逐步调整作息'},
            {'name': '调整期', 'duration': '4天', 'focus': '推进目标参数，观察宝宝反应'},
            {'name': '巩固期', 'duration': f"{max(0, params['sim_duration_days'] - 10)}天" if params['sim_duration_days'] > 10 else '视情况', 'focus': '稳定执行，形成生物钟'},
            {'name': '稳定期', 'duration': '剩余天数', 'focus': '维持规律，定期评估'},
        ],
        'key_actions': [p for p in priorities if p.get('priority') in ['high', 'medium']],
        'expected_outcomes': {
            '夜醒减少': f"{prediction['changes']['night_waking_reduction_pct']}%",
            '总睡眠增加': f"{prediction['changes']['total_sleep_change_minutes']} 分钟/天",
            '稳定度提升': f"{prediction['changes']['stability_gain']} 分",
        },
        'risks': risks,
    }
    return summary


def _generate_plan_name(params, priorities):
    if not priorities:
        return '综合睡眠改善方案'
    
    top = priorities[0]
    if top['key'] == 'bedtime':
        return '规律作息调整方案'
    elif top['key'] == 'soothing':
        return '夜醒安抚训练方案'
    elif top['key'] == 'nap_count':
        return '小睡优化方案'
    elif top['key'] == 'last_nap':
        return '晚间作息调整方案'
    elif top['key'] == 'milk':
        return '喂养调整改善方案'
    else:
        return '综合睡眠改善方案'


def generate_baseline_summary(baseline, stats):
    return {
        '记录天数': f"{baseline.get('days_recorded', 0)} 天",
        '平均总睡眠': f"{baseline.get('avg_total_sleep_hours', 0)} 小时/天",
        '平均夜间睡眠': f"{baseline.get('avg_night_sleep_hours', 0)} 小时",
        '平均夜醒次数': f"{baseline.get('avg_nightwakings', 0)} 次/夜",
        '夜醒天数占比': f"{baseline.get('night_waking_days_pct', 0)}%",
        '平均小睡次数': f"{baseline.get('avg_naps_count', 0)} 次",
        '平均奶量': f"{baseline.get('avg_milk_ml', 0):.0f} ml/天" if baseline.get('avg_milk_ml') else '未记录',
        '作息稳定度': f"{baseline.get('stability_score', 0)} 分",
        '平均入睡时间': minutes_to_time_display(baseline.get('avg_bedtime_minutes', 0)),
        '平均起床时间': minutes_to_time_display(baseline.get('avg_wakeup_minutes', 0)),
    }
