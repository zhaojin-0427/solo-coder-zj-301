import pandas as pd
import numpy as np
from data_processor import minutes_to_time_display


SIM_DURATION_OPTIONS = [7, 14, 30]

SOOTHING_STRATEGY_LEVELS = {
    '轻柔安抚': {'intensity': 1, 'description': '轻拍、安抚奶嘴、白噪音，不抱起'},
    '适度安抚': {'intensity': 2, 'description': '抱起安抚后放下，逐步延长响应时间'},
    '渐进式训练': {'intensity': 3, 'description': '哭声免疫法变体，逐步拉长安抚间隔'},
}


def get_default_intervention_params(filtered_df, stats, stability, patterns):
    if filtered_df is None or len(filtered_df) == 0:
        return {}
    
    bt_mean = filtered_df['bedtime_minutes'].mean()
    wt_mean = filtered_df['wakeup_minutes'].mean()
    nap_count = filtered_df['naps_count'].mean()
    milk_avg = filtered_df['milk_amount_ml'].mean() if filtered_df['milk_amount_ml'].notna().any() else 0
    
    last_nap_avg = filtered_df['last_nap_minutes'].dropna().mean()
    if pd.isna(last_nap_avg):
        last_nap_avg = 14 * 60
    
    nw_avg = filtered_df['nightwakings'].mean()
    
    if nw_avg <= 1:
        default_soothing = '轻柔安抚'
    elif nw_avg <= 3:
        default_soothing = '适度安抚'
    else:
        default_soothing = '渐进式训练'
    
    return {
        'target_bedtime_start': int(round(bt_mean - 30)),
        'target_bedtime_end': int(round(bt_mean + 15)),
        'last_nap_deadline': int(round(min(last_nap_avg, 15 * 60))),
        'nap_count_adjustment': 0,
        'milk_change_pct': 0,
        'soothing_strategy': default_soothing,
        'sim_duration_days': 14,
    }


def validate_params(params):
    errors = []
    if not isinstance(params.get('sim_duration_days'), int):
        errors.append('模拟天数必须是整数')
    elif params['sim_duration_days'] not in SIM_DURATION_OPTIONS:
        errors.append(f'模拟天数必须是 {SIM_DURATION_OPTIONS} 之一')
    
    if params.get('target_bedtime_start', 0) >= params.get('target_bedtime_end', 0):
        errors.append('入睡窗口开始时间必须早于结束时间')
    
    nap_adj = params.get('nap_count_adjustment', 0)
    if not isinstance(nap_adj, (int, float)) or abs(nap_adj) > 3:
        errors.append('小睡次数调整幅度不合理（±3次以内）')
    
    milk_pct = params.get('milk_change_pct', 0)
    if not isinstance(milk_pct, (int, float)) or abs(milk_pct) > 50:
        errors.append('奶量变化比例不合理（±50%以内）')
    
    if params.get('soothing_strategy') not in SOOTHING_STRATEGY_LEVELS:
        errors.append('无效的夜醒安抚策略')
    
    return errors


def get_param_display(params, stats):
    bt_start = minutes_to_time_display(params['target_bedtime_start'])
    bt_end = minutes_to_time_display(params['target_bedtime_end'])
    last_nap = minutes_to_time_display(params['last_nap_deadline'])
    
    nap_adj = params['nap_count_adjustment']
    if nap_adj > 0:
        nap_text = f'增加 {nap_adj} 次'
    elif nap_adj < 0:
        nap_text = f'减少 {abs(nap_adj)} 次'
    else:
        nap_text = '保持不变'
    
    milk_pct = params['milk_change_pct']
    if milk_pct > 0:
        milk_text = f'增加 {milk_pct}%'
    elif milk_pct < 0:
        milk_text = f'减少 {abs(milk_pct)}%'
    else:
        milk_text = '保持不变'
    
    return {
        'bedtime_window': f'{bt_start} ~ {bt_end}',
        'last_nap_deadline': last_nap,
        'nap_adjustment': nap_text,
        'milk_change': milk_text,
        'soothing_strategy': params['soothing_strategy'],
        'sim_duration': f"{params['sim_duration_days']} 天",
    }


def get_intervention_dimensions():
    return [
        {'key': 'bedtime', 'name': '入睡窗口调整', 'weight': 0.25, 'icon': '🛌'},
        {'key': 'last_nap', 'name': '最后一觉限制', 'weight': 0.15, 'icon': '⏰'},
        {'key': 'nap_count', 'name': '白天小睡调整', 'weight': 0.2, 'icon': '😴'},
        {'key': 'milk', 'name': '奶量调整', 'weight': 0.15, 'icon': '🍼'},
        {'key': 'soothing', 'name': '夜醒安抚策略', 'weight': 0.25, 'icon': '💆'},
    ]
