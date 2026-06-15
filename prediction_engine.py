import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processor import minutes_to_time_display
from analyzer import compute_stability_score, compute_basic_stats, detect_patterns
from intervention_params import SOOTHING_STRATEGY_LEVELS, get_intervention_dimensions


def compute_baseline_metrics(filtered_df):
    if filtered_df is None or len(filtered_df) == 0:
        return {}
    
    stats = compute_basic_stats(filtered_df)
    stability = compute_stability_score(filtered_df)
    patterns = detect_patterns(filtered_df)
    
    nw_period_counts = {}
    for periods in filtered_df.get('nw_periods_list', []):
        for p in periods:
            nw_period_counts[p] = nw_period_counts.get(p, 0) + 1
    
    baseline = {
        'avg_nightwakings': stats['avg_nightwakings'],
        'avg_total_sleep_hours': stats['avg_total_sleep_hours'],
        'avg_night_sleep_hours': stats['avg_night_sleep_hours'],
        'avg_nap_hours': stats['avg_nap_hours'],
        'avg_bedtime_minutes': filtered_df['bedtime_minutes'].mean(),
        'avg_wakeup_minutes': filtered_df['wakeup_minutes'].mean(),
        'stability_score': stability['overall'],
        'stability_details': stability,
        'avg_naps_count': stats['avg_naps_count'],
        'avg_milk_ml': stats['avg_milk_ml'],
        'night_waking_days_pct': stats['night_waking_days_pct'],
        'nw_period_distribution': nw_period_counts,
        'patterns': patterns,
        'days_recorded': stats['days_recorded'],
        'bedtime_std_minutes': filtered_df['bedtime_minutes'].std() if len(filtered_df) > 1 else 60,
    }
    
    return baseline


def compute_intervention_effects(filtered_df, baseline, params):
    effects = {}
    
    bt_target_mid = (params['target_bedtime_start'] + params['target_bedtime_end']) / 2
    bt_current = baseline['avg_bedtime_minutes']
    bt_diff = abs(bt_target_mid - bt_current)
    
    bt_std_current = baseline.get('bedtime_std_minutes', 60)
    target_window = params['target_bedtime_end'] - params['target_bedtime_start']
    if target_window < 60:
        bt_effectiveness = min(1.0, (bt_std_current - 30) / 120 + 0.3)
    else:
        bt_effectiveness = min(1.0, (bt_std_current - target_window / 2) / 120 + 0.2)
    
    if bt_diff > 180:
        bt_risk = 'high'
        bt_nw_reduction_pct = -5
    elif bt_diff > 90:
        bt_risk = 'medium'
        bt_nw_reduction_pct = 8
    else:
        bt_risk = 'low'
        bt_nw_reduction_pct = 15
    
    bt_stability_gain = min(25, bt_effectiveness * 25)
    
    effects['bedtime'] = {
        'night_waking_reduction_pct': bt_nw_reduction_pct * bt_effectiveness,
        'total_sleep_change_minutes': 15 * bt_effectiveness,
        'stability_gain': bt_stability_gain,
        'risk_level': bt_risk,
        'effectiveness': bt_effectiveness,
    }
    
    last_nap_current = filtered_df['last_nap_minutes'].dropna().mean()
    if pd.isna(last_nap_current):
        last_nap_current = 15 * 60
    
    last_nap_target = params['last_nap_deadline']
    last_nap_diff = last_nap_current - last_nap_target
    
    if last_nap_diff > 60:
        ln_nw_reduction = 20
        ln_sleep_change = 20
        ln_risk = 'low'
    elif last_nap_diff > 30:
        ln_nw_reduction = 12
        ln_sleep_change = 10
        ln_risk = 'low'
    elif last_nap_diff > 0:
        ln_nw_reduction = 5
        ln_sleep_change = 5
        ln_risk = 'low'
    else:
        ln_nw_reduction = 0
        ln_sleep_change = 0
        ln_risk = 'low'
    
    effects['last_nap'] = {
        'night_waking_reduction_pct': ln_nw_reduction,
        'total_sleep_change_minutes': ln_sleep_change,
        'stability_gain': 8 if last_nap_diff > 0 else 0,
        'risk_level': ln_risk,
        'effectiveness': min(1.0, abs(last_nap_diff) / 120),
    }
    
    nap_adj = params['nap_count_adjustment']
    current_naps = baseline['avg_naps_count']
    
    if nap_adj < 0:
        if current_naps <= 1:
            nap_nw_change = 10
            nap_sleep_change = -30
            nap_risk = 'high'
            nap_stability = -5
        else:
            nap_nw_change = -10 * abs(nap_adj)
            nap_sleep_change = 20 * abs(nap_adj)
            nap_risk = 'medium'
            nap_stability = 5 * abs(nap_adj)
    elif nap_adj > 0:
        if current_naps >= 4:
            nap_nw_change = 15
            nap_sleep_change = -15
            nap_risk = 'medium'
            nap_stability = -3
        else:
            nap_nw_change = -5 * nap_adj
            nap_sleep_change = 15 * nap_adj
            nap_risk = 'low'
            nap_stability = 3 * nap_adj
    else:
        nap_nw_change = 0
        nap_sleep_change = 0
        nap_risk = 'low'
        nap_stability = 0
    
    effects['nap_count'] = {
        'night_waking_reduction_pct': nap_nw_change,
        'total_sleep_change_minutes': nap_sleep_change,
        'stability_gain': nap_stability,
        'risk_level': nap_risk,
        'effectiveness': 0.7,
    }
    
    milk_pct = params['milk_change_pct']
    current_milk = baseline.get('avg_milk_ml', 0)
    
    if current_milk is None or pd.isna(current_milk) or current_milk == 0:
        milk_effect = 0
        milk_sleep_change = 0
        milk_risk = 'low'
        milk_stability = 0
    else:
        if milk_pct > 0:
            if current_milk >= 1000:
                milk_effect = 2
                milk_sleep_change = 5
                milk_risk = 'medium'
            else:
                milk_effect = -8 * min(1, milk_pct / 20)
                milk_sleep_change = 10 * min(1, milk_pct / 20)
                milk_risk = 'low'
            milk_stability = 2 * min(1, milk_pct / 20)
        elif milk_pct < 0:
            milk_effect = 10 * min(1, abs(milk_pct) / 30)
            milk_sleep_change = -15 * min(1, abs(milk_pct) / 30)
            milk_risk = 'medium'
            milk_stability = -3 * min(1, abs(milk_pct) / 30)
        else:
            milk_effect = 0
            milk_sleep_change = 0
            milk_risk = 'low'
            milk_stability = 0
    
    effects['milk'] = {
        'night_waking_reduction_pct': milk_effect,
        'total_sleep_change_minutes': milk_sleep_change,
        'stability_gain': milk_stability,
        'risk_level': milk_risk,
        'effectiveness': 0.8,
    }
    
    strategy = params['soothing_strategy']
    intensity = SOOTHING_STRATEGY_LEVELS[strategy]['intensity']
    current_nw = baseline['avg_nightwakings']
    
    if current_nw < 1:
        soothing_effect = 0
        soothing_risk = 'low'
        soothing_stability = 2
    else:
        base_reduction = [5, 18, 30][intensity - 1]
        if current_nw > 3:
            soothing_effect = base_reduction * 1.2
        elif current_nw > 1.5:
            soothing_effect = base_reduction
        else:
            soothing_effect = base_reduction * 0.6
        
        soothing_risk = ['low', 'medium', 'high'][intensity - 1]
        soothing_stability = [3, 8, 12][intensity - 1]
    
    effects['soothing'] = {
        'night_waking_reduction_pct': soothing_effect,
        'total_sleep_change_minutes': [5, 20, 35][intensity - 1],
        'stability_gain': soothing_stability,
        'risk_level': soothing_risk,
        'effectiveness': [0.9, 0.8, 0.7][intensity - 1],
    }
    
    return effects


def compute_combined_prediction(baseline, effects, params):
    dims = get_intervention_dimensions()
    
    total_nw_reduction_pct = 0
    total_sleep_change = 0
    total_stability_gain = 0
    max_risk = 'low'
    
    risk_order = {'low': 0, 'medium': 1, 'high': 2}
    
    dimension_effects = {}
    for dim in dims:
        key = dim['key']
        weight = dim['weight']
        eff = effects.get(key, {})
        
        nw_pct = eff.get('night_waking_reduction_pct', 0)
        sleep_min = eff.get('total_sleep_change_minutes', 0)
        stab_gain = eff.get('stability_gain', 0)
        
        total_nw_reduction_pct += nw_pct * weight
        total_sleep_change += sleep_min * weight
        total_stability_gain += stab_gain * weight
        
        risk = eff.get('risk_level', 'low')
        if risk_order.get(risk, 0) > risk_order.get(max_risk, 0):
            max_risk = risk
        
        dimension_effects[key] = {
            'name': dim['name'],
            'icon': dim['icon'],
            'nw_reduction_pct_contribution': round(nw_pct * weight, 1),
            'sleep_change_contribution': round(sleep_min * weight, 1),
            'stability_contribution': round(stab_gain * weight, 1),
            'risk_level': risk,
            'effectiveness': eff.get('effectiveness', 0.5),
        }
    
    saturation_factor = 1.0
    if total_nw_reduction_pct > 40:
        saturation_factor = 0.7 + 0.3 * (40 / max(total_nw_reduction_pct, 1))
    total_nw_reduction_pct *= saturation_factor
    
    base_nw = baseline['avg_nightwakings']
    predicted_nw = max(0.1, base_nw * (1 - total_nw_reduction_pct / 100))
    
    base_sleep = baseline['avg_total_sleep_hours']
    predicted_sleep = base_sleep + total_sleep_change / 60
    
    base_stability = baseline['stability_score']
    predicted_stability = min(100, base_stability + total_stability_gain)
    
    return {
        'baseline': {
            'avg_nightwakings': base_nw,
            'avg_total_sleep_hours': base_sleep,
            'stability_score': base_stability,
        },
        'predicted': {
            'avg_nightwakings': round(predicted_nw, 2),
            'avg_total_sleep_hours': round(predicted_sleep, 1),
            'stability_score': round(predicted_stability, 1),
        },
        'changes': {
            'night_waking_reduction_abs': round(base_nw - predicted_nw, 2),
            'night_waking_reduction_pct': round(total_nw_reduction_pct, 1),
            'total_sleep_change_minutes': round(total_sleep_change, 1),
            'total_sleep_change_pct': round((total_sleep_change / 60) / base_sleep * 100, 1) if base_sleep > 0 else 0,
            'stability_gain': round(total_stability_gain, 1),
        },
        'overall_risk_level': max_risk,
        'dimension_effects': dimension_effects,
        'sim_duration_days': params['sim_duration_days'],
    }


def generate_daily_prediction_series(baseline, effects, params):
    days = params['sim_duration_days']
    base_nw = baseline['avg_nightwakings']
    base_sleep = baseline['avg_total_sleep_hours']
    base_stab = baseline['stability_score']
    
    dates = []
    predicted_nw = []
    predicted_sleep = []
    predicted_stab = []
    
    dims = get_intervention_dimensions()
    
    total_nw_pct = 0
    total_sleep_min = 0
    total_stab_gain = 0
    
    for dim in dims:
        eff = effects.get(dim['key'], {})
        total_nw_pct += eff.get('night_waking_reduction_pct', 0) * dim['weight']
        total_sleep_min += eff.get('total_sleep_change_minutes', 0) * dim['weight']
        total_stab_gain += eff.get('stability_gain', 0) * dim['weight']
    
    if total_nw_pct > 40:
        saturation = 0.7 + 0.3 * (40 / max(total_nw_pct, 1))
        total_nw_pct *= saturation
    
    for day in range(1, days + 1):
        progress = min(1.0, day / max(days * 0.7, 7))
        
        adaptation_curve = 1 - np.exp(-day / 5)
        
        effective_progress = progress * 0.7 + adaptation_curve * 0.3
        
        noise_nw = np.random.normal(0, base_nw * 0.15)
        noise_sleep = np.random.normal(0, 0.3)
        
        day_nw = max(0.1, base_nw * (1 - total_nw_pct / 100 * effective_progress) + noise_nw)
        day_sleep = base_sleep + (total_sleep_min / 60) * effective_progress + noise_sleep
        day_stab = min(100, base_stab + total_stab_gain * effective_progress)
        
        dates.append(f'第 {day} 天')
        predicted_nw.append(round(day_nw, 2))
        predicted_sleep.append(round(day_sleep, 2))
        predicted_stab.append(round(day_stab, 1))
    
    return {
        'days': dates,
        'nightwakings': predicted_nw,
        'total_sleep_hours': predicted_sleep,
        'stability_score': predicted_stab,
    }


def generate_risk_warnings(baseline, effects, params):
    warnings = []
    
    overall_risk = effects.get('soothing', {}).get('risk_level', 'low')
    if overall_risk == 'high':
        warnings.append({
            'level': 'high',
            'title': '高强度睡眠训练风险',
            'detail': '渐进式训练可能导致宝宝哭闹增加，建议在宝宝健康状况良好时开始，家长需做好心理准备。'
        })
    elif overall_risk == 'medium':
        warnings.append({
            'level': 'medium',
            'title': '调整期可能出现暂时波动',
            'detail': '安抚策略改变初期可能出现夜醒暂时增加，通常3-5天后会逐渐改善。'
        })
    
    bt_diff = abs((params['target_bedtime_start'] + params['target_bedtime_end']) / 2 
                  - baseline['avg_bedtime_minutes'])
    if bt_diff > 120:
        warnings.append({
            'level': 'medium',
            'title': '入睡时间调整幅度过大',
            'detail': f'当前目标入睡时间与实际平均相差超过2小时，建议每周调整不超过30分钟，逐步过渡。'
        })
    
    nap_adj = params['nap_count_adjustment']
    current_naps = baseline['avg_naps_count']
    if nap_adj < 0 and current_naps <= 2:
        warnings.append({
            'level': 'high',
            'title': '小睡次数减少需谨慎',
            'detail': '当前小睡次数已偏少，强行减少可能导致过度疲劳，反而增加夜醒。'
        })
    
    milk_pct = params['milk_change_pct']
    if milk_pct < -20:
        warnings.append({
            'level': 'high',
            'title': '奶量减少幅度过大',
            'detail': '奶量大幅减少可能导致饥饿性夜醒，建议循序渐进，每周减少不超过10%。'
        })
    
    last_nap_target = params['last_nap_deadline']
    last_nap_current = baseline.get('avg_bedtime_minutes', 15 * 60)
    if last_nap_target < 12 * 60:
        warnings.append({
            'level': 'medium',
            'title': '最后一觉结束时间过早',
            'detail': '12点前结束最后一觉可能导致睡前过度疲劳，建议根据宝宝实际情况调整。'
        })
    
    if baseline['stability_score'] < 40:
        warnings.append({
            'level': 'medium',
            'title': '当前作息稳定性较差',
            'detail': '稳定度低于40分，建议优先固定起床时间，再逐步调整其他参数。'
        })
    
    if not warnings:
        warnings.append({
            'level': 'low',
            'title': '干预方案整体风险较低',
            'detail': '各项参数调整在合理范围内，预计宝宝适应良好。'
        })
    
    return warnings


def compute_action_priority(filtered_df, baseline, effects, params):
    dims = get_intervention_dimensions()
    priorities = []
    
    current_nw = baseline['avg_nightwakings']
    has_late_nap_pattern = any('最后一觉' in p.get('title', '') for p in baseline.get('patterns', []))
    has_teething_issue = any('长牙' in p.get('title', '') for p in baseline.get('patterns', []))
    has_milk_issue = any('奶量' in p.get('title', '') for p in baseline.get('patterns', []))
    
    for dim in dims:
        key = dim['key']
        eff = effects.get(key, {})
        nw_impact = abs(eff.get('night_waking_reduction_pct', 0))
        risk = eff.get('risk_level', 'low')
        
        risk_penalty = {'low': 0, 'medium': 0.3, 'high': 0.6}[risk]
        effectiveness = eff.get('effectiveness', 0.5)
        
        score = nw_impact * effectiveness * (1 - risk_penalty)
        
        if key == 'last_nap' and has_late_nap_pattern:
            score *= 1.3
        if key == 'milk' and has_milk_issue:
            score *= 1.2
        if key == 'bedtime' and baseline['stability_score'] < 60:
            score *= 1.2
        
        if key == 'soothing' and current_nw < 1:
            score *= 0.3
        
        priorities.append({
            'key': key,
            'name': dim['name'],
            'icon': dim['icon'],
            'score': round(score, 1),
            'risk_level': risk,
            'night_waking_impact_pct': round(nw_impact, 1),
            'sleep_impact_minutes': round(eff.get('total_sleep_change_minutes', 0), 1),
        })
    
    priorities.sort(key=lambda x: x['score'], reverse=True)
    
    for i, p in enumerate(priorities):
        if i == 0 and p['score'] > 10:
            p['priority'] = 'high'
            p['priority_label'] = '最高优先'
        elif i <= 1 and p['score'] > 5:
            p['priority'] = 'medium'
            p['priority_label'] = '中等优先'
        else:
            p['priority'] = 'low'
            p['priority_label'] = '较低优先'
    
    return priorities
