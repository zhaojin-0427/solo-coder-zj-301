import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processor import minutes_to_time_display
from analyzer import compute_basic_stats, compute_stability_score


PHASE_MODES = ['自然周', '自然月', '自定义阶段', '干预前后']


def get_week_boundaries(date):
    start = date - timedelta(days=date.weekday())
    end = start + timedelta(days=6)
    return start.date(), end.date()


def get_month_boundaries(date):
    start = date.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
    return start.date(), end.date()


def generate_phase_options(df, mode='自然周', custom_phases=None):
    if len(df) == 0:
        return []
    
    df = df.sort_values('date').reset_index(drop=True)
    phases = []
    
    if mode == '自然周':
        seen_weeks = set()
        for _, row in df.iterrows():
            d = row['date']
            w_start, w_end = get_week_boundaries(d)
            week_key = (w_start, w_end)
            if week_key not in seen_weeks:
                seen_weeks.add(week_key)
                week_num = d.isocalendar()[1]
                phases.append({
                    'name': f'第{week_num}周 ({w_start.strftime("%m-%d")}~{w_end.strftime("%m-%d")})',
                    'start_date': w_start,
                    'end_date': w_end,
                    'type': 'week'
                })
                
    elif mode == '自然月':
        seen_months = set()
        for _, row in df.iterrows():
            d = row['date']
            m_start, m_end = get_month_boundaries(d)
            month_key = (m_start.year, m_start.month)
            if month_key not in seen_months:
                seen_months.add(month_key)
                phases.append({
                    'name': f'{m_start.year}年{m_start.month}月',
                    'start_date': m_start,
                    'end_date': m_end,
                    'type': 'month'
                })
                
    elif mode == '自定义阶段' and custom_phases:
        for i, cp in enumerate(custom_phases):
            phases.append({
                'name': cp.get('name', f'阶段{i+1}'),
                'start_date': cp.get('start_date'),
                'end_date': cp.get('end_date'),
                'type': 'custom'
            })
            
    elif mode == '干预前后':
        phases.append({
            'name': '干预前（基线）',
            'start_date': None,
            'end_date': None,
            'type': 'pre_intervention'
        })
        phases.append({
            'name': '干预后',
            'start_date': None,
            'end_date': None,
            'type': 'post_intervention'
        })
    
    return phases


def filter_by_phase(df, start_date, end_date):
    filtered = df.copy()
    if start_date:
        filtered = filtered[filtered['date'] >= pd.to_datetime(start_date)]
    if end_date:
        filtered = filtered[filtered['date'] <= pd.to_datetime(end_date) + pd.Timedelta(days=1)]
    return filtered.reset_index(drop=True)


def compute_phase_metrics(df_phase, phase_name=''):
    result = {
        'phase_name': phase_name,
        'days_count': len(df_phase),
        'date_range': None,
        'metrics': {},
        'stability': {},
        'nw_period_distribution': {},
        'milk_nw_correlation': None,
        'status': '数据不足'
    }
    
    if len(df_phase) < 3:
        return result
    
    result['date_range'] = (
        df_phase['date'].min().strftime('%Y-%m-%d'),
        df_phase['date'].max().strftime('%Y-%m-%d')
    )
    
    stats = compute_basic_stats(df_phase)
    stability = compute_stability_score(df_phase)
    
    avg_last_nap = df_phase['last_nap_minutes'].dropna().mean()
    bedtime_std = df_phase['bedtime_minutes'].std() if len(df_phase) > 1 else np.nan
    
    result['metrics'] = {
        'avg_total_sleep_hours': stats.get('avg_total_sleep_hours', 0),
        'avg_night_sleep_hours': stats.get('avg_night_sleep_hours', 0),
        'avg_nap_hours': stats.get('avg_nap_hours', 0),
        'avg_nightwakings': stats.get('avg_nightwakings', 0),
        'night_waking_days_pct': stats.get('night_waking_days_pct', 0),
        'avg_bedtime': stats.get('avg_bedtime', ''),
        'avg_bedtime_minutes': df_phase['bedtime_minutes'].mean(),
        'avg_wakeup': stats.get('avg_wakeup', ''),
        'avg_wakeup_minutes': df_phase['wakeup_minutes'].mean(),
        'avg_naps_count': stats.get('avg_naps_count', 0),
        'avg_milk_ml': stats.get('avg_milk_ml', 0),
        'avg_last_nap_end': minutes_to_time_display(avg_last_nap) if pd.notna(avg_last_nap) else '',
        'avg_last_nap_minutes': avg_last_nap if pd.notna(avg_last_nap) else np.nan,
        'bedtime_std_minutes': bedtime_std if pd.notna(bedtime_std) else 0,
        'bedtime_window_stability': max(0, 100 - (bedtime_std / 120) * 100) if pd.notna(bedtime_std) else 50,
    }
    
    result['stability'] = stability
    
    nw_counts = {}
    for periods in df_phase.get('nw_periods_list', []):
        for p in periods:
            nw_counts[p] = nw_counts.get(p, 0) + 1
    result['nw_period_distribution'] = nw_counts
    
    milk_valid = df_phase.dropna(subset=['milk_amount_ml', 'nightwakings'])
    if len(milk_valid) >= 5:
        corr = milk_valid['milk_amount_ml'].corr(milk_valid['nightwakings'])
        result['milk_nw_correlation'] = round(corr, 3) if pd.notna(corr) else None
    
    if len(df_phase) >= 5:
        result['status'] = assess_phase_status(df_phase, result)
    
    return result


def assess_phase_status(df_phase, phase_result):
    metrics = phase_result['metrics']
    stability_score = phase_result['stability'].get('overall', 50)
    
    if len(df_phase) < 5:
        return '数据不足'
    
    nw_series = df_phase['nightwakings'].values
    if len(nw_series) >= 5:
        half = len(nw_series) // 2
        first_half_avg = nw_series[:half].mean()
        second_half_avg = nw_series[half:].mean()
        
        nw_change_pct = (second_half_avg - first_half_avg) / max(first_half_avg, 0.1) * 100
        
        nw_std = nw_series.std()
        nw_cv = nw_std / max(nw_series.mean(), 0.1)
        
        if nw_change_pct <= -15:
            if stability_score >= 60:
                return '改善中'
            else:
                return '改善中（稳定性待提升）'
        elif nw_change_pct >= 20:
            return '阶段倒退'
        elif abs(nw_change_pct) < 15 and nw_cv > 0.5:
            return '反复波动'
        elif stability_score >= 70 and nw_cv < 0.4:
            return '稳定良好'
        elif stability_score < 40:
            return '不稳定'
    
    return '观察中'


def compare_phases(phase_results_list):
    if len(phase_results_list) < 2:
        return {}
    
    comparison = {}
    base = phase_results_list[0]
    
    for i, pr in enumerate(phase_results_list[1:], 1):
        label = f'{base["phase_name"]} vs {pr["phase_name"]}'
        changes = {}
        
        base_m = base['metrics']
        comp_m = pr['metrics']
        
        for key in ['avg_total_sleep_hours', 'avg_night_sleep_hours', 'avg_nap_hours',
                    'avg_nightwakings', 'bedtime_window_stability', 'avg_milk_ml',
                    'avg_naps_count', 'night_waking_days_pct']:
            base_val = base_m.get(key, 0) or 0
            comp_val = comp_m.get(key, 0) or 0
            diff = comp_val - base_val
            pct = (diff / max(base_val, 0.01)) * 100 if base_val != 0 else 0
            changes[key] = {
                'base': round(base_val, 2),
                'compare': round(comp_val, 2),
                'diff': round(diff, 2),
                'pct': round(pct, 1)
            }
        
        base_stab = base['stability'].get('overall', 50)
        comp_stab = pr['stability'].get('overall', 50)
        changes['stability_score'] = {
            'base': round(base_stab, 1),
            'compare': round(comp_stab, 1),
            'diff': round(comp_stab - base_stab, 1),
            'pct': round((comp_stab - base_stab) / max(base_stab, 0.1) * 100, 1)
        }
        
        base_last_nap = base_m.get('avg_last_nap_minutes', np.nan)
        comp_last_nap = comp_m.get('avg_last_nap_minutes', np.nan)
        if pd.notna(base_last_nap) and pd.notna(comp_last_nap):
            diff = comp_last_nap - base_last_nap
            changes['last_nap_minutes'] = {
                'base': round(base_last_nap, 1),
                'compare': round(comp_last_nap, 1),
                'diff': round(diff, 1),
                'base_display': minutes_to_time_display(base_last_nap),
                'compare_display': minutes_to_time_display(comp_last_nap)
            }
        
        comparison[label] = changes
    
    return comparison


def generate_phase_summary(phase_results, comparison):
    summary = {
        'key_changes': [],
        'overall_assessment': '',
        'recommendations': []
    }
    
    if len(phase_results) < 2:
        summary['overall_assessment'] = '至少需要两个阶段才能进行对比分析'
        return summary
    
    latest = phase_results[-1]
    base = phase_results[0]
    latest_status = latest.get('status', '数据不足')
    
    if comparison:
        first_key = list(comparison.keys())[0]
        changes = comparison[first_key]
        
        nw = changes.get('avg_nightwakings', {})
        if nw.get('diff', 0) < 0:
            summary['key_changes'].append(
                f'✅ 夜醒次数减少：从{nw.get("base", 0):.1f}次降至{nw.get("compare", 0):.1f}次（{abs(nw.get("pct", 0)):.1f}%）'
            )
        elif nw.get('diff', 0) > 0:
            summary['key_changes'].append(
                f'⚠️ 夜醒次数增加：从{nw.get("base", 0):.1f}次升至{nw.get("compare", 0):.1f}次（+{nw.get("pct", 0):.1f}%）'
            )
        
        total_sleep = changes.get('avg_total_sleep_hours', {})
        if total_sleep.get('diff', 0) > 0:
            summary['key_changes'].append(
                f'✅ 总睡眠时长增加：+{total_sleep.get("diff", 0):.1f}小时/天'
            )
        elif total_sleep.get('diff', 0) < 0:
            summary['key_changes'].append(
                f'⚠️ 总睡眠时长减少：{total_sleep.get("diff", 0):.1f}小时/天'
            )
        
        stab = changes.get('stability_score', {})
        if stab.get('diff', 0) > 5:
            summary['key_changes'].append(
                f'✅ 作息稳定度提升：+{stab.get("diff", 0):.1f}分'
            )
        elif stab.get('diff', 0) < -5:
            summary['key_changes'].append(
                f'⚠️ 作息稳定度下降：{stab.get("diff", 0):.1f}分'
            )
    
    if '改善' in latest_status:
        summary['overall_assessment'] = f'🎉 当前阶段状态：{latest_status}，改善趋势明显，请继续保持现有策略'
        summary['recommendations'].append('继续保持当前有效的作息规律和干预措施')
        summary['recommendations'].append('观察是否进入稳定期，巩固已取得的成果')
    elif '倒退' in latest_status:
        summary['overall_assessment'] = f'📉 当前阶段状态：{latest_status}，需要关注可能的退步原因'
        summary['recommendations'].append('排查近期是否有生病、长牙、环境变化等干扰因素')
        summary['recommendations'].append('回顾之前有效的措施，考虑重新恢复执行')
        summary['recommendations'].append('如持续倒退超过1周，建议调整干预策略')
    elif '波动' in latest_status:
        summary['overall_assessment'] = f'📊 当前阶段状态：{latest_status}，数据起伏较大，需要更细致的观察'
        summary['recommendations'].append('记录每天可能影响睡眠的变量（天气、外出、访客等）')
        summary['recommendations'].append('尝试固定所有作息环节，减少变量')
        summary['recommendations'].append('延长观察周期，排除偶然波动')
    elif latest_status == '稳定良好':
        summary['overall_assessment'] = f'🌟 当前阶段状态：{latest_status}，睡眠质量良好'
        summary['recommendations'].append('保持当前作息规律，形成稳定的生物钟')
        summary['recommendations'].append('可根据月龄变化适时调整小睡次数和时长')
    else:
        summary['overall_assessment'] = f'🔍 当前阶段状态：{latest_status}，建议继续记录观察'
        summary['recommendations'].append('持续记录至少7天以获得更可靠的分析')
        summary['recommendations'].append('关注入睡时间是否固定，这通常是改善的起点')
    
    base_milk_corr = base.get('milk_nw_correlation')
    latest_milk_corr = latest.get('milk_nw_correlation')
    if base_milk_corr is not None and latest_milk_corr is not None:
        if latest_milk_corr < -0.3 and base_milk_corr >= -0.3:
            summary['key_changes'].append(
                f'🔍 奶量与夜醒的负相关增强（相关系数: {latest_milk_corr}），奶量增加可能有助于减少夜醒'
            )
    
    return summary


def compute_intervention_vs_prediction(intervention_phase_df, prediction_result):
    if len(intervention_phase_df) < 3 or not prediction_result:
        return {}
    
    actual_stats = compute_basic_stats(intervention_phase_df)
    actual_stability = compute_stability_score(intervention_phase_df)
    
    predicted = prediction_result.get('predicted', {})
    baseline = prediction_result.get('baseline', {})
    
    comparison = {
        'nightwakings': {
            'predicted': predicted.get('avg_nightwakings', 0),
            'actual': actual_stats.get('avg_nightwakings', 0),
            'baseline': baseline.get('avg_nightwakings', 0),
            'diff_pred_actual': 0,
            'achievement_pct': 0
        },
        'total_sleep_hours': {
            'predicted': predicted.get('avg_total_sleep_hours', 0),
            'actual': actual_stats.get('avg_total_sleep_hours', 0),
            'baseline': baseline.get('avg_total_sleep_hours', 0),
            'diff_pred_actual': 0,
            'achievement_pct': 0
        },
        'stability_score': {
            'predicted': predicted.get('stability_score', 0),
            'actual': actual_stability.get('overall', 0),
            'baseline': baseline.get('stability_score', 0),
            'diff_pred_actual': 0,
            'achievement_pct': 0
        }
    }
    
    for key in comparison:
        item = comparison[key]
        item['predicted'] = round(item.get('predicted', 0) or 0, 2)
        item['actual'] = round(item.get('actual', 0) or 0, 2)
        item['baseline'] = round(item.get('baseline', 0) or 0, 2)
        item['diff_pred_actual'] = round(item['actual'] - item['predicted'], 2)
        
        if key == 'nightwakings':
            pred_improvement = item['baseline'] - item['predicted']
            actual_improvement = item['baseline'] - item['actual']
            target_direction = 'decrease'
        else:
            pred_improvement = item['predicted'] - item['baseline']
            actual_improvement = item['actual'] - item['baseline']
            target_direction = 'increase'
        
        if pd.isna(pred_improvement) or pd.isna(actual_improvement) or np.isinf(pred_improvement) or np.isinf(actual_improvement):
            item['achievement_pct'] = 0.0
        elif abs(pred_improvement) < 0.05:
            if abs(actual_improvement) < 0.05:
                item['achievement_pct'] = 100.0
            else:
                actual_positive = (target_direction == 'decrease' and actual_improvement > 0) or \
                                  (target_direction == 'increase' and actual_improvement > 0)
                if actual_positive:
                    item['achievement_pct'] = 100.0
                else:
                    item['achievement_pct'] = 0.0
        else:
            raw_pct = actual_improvement / pred_improvement * 100
            if pd.isna(raw_pct) or np.isinf(raw_pct):
                item['achievement_pct'] = 0.0
            else:
                item['achievement_pct'] = round(max(0, min(150, raw_pct)), 1)
                if item['achievement_pct'] < 0:
                    item['achievement_pct'] = 0.0
    
    return comparison
