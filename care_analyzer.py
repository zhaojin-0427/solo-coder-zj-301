import pandas as pd
import numpy as np
from care_data_processor import BEDTIME_ROUTINE_ITEMS, SOOTHING_METHODS, NW_RESPONSES


def compute_handover_timeline(care_df):
    if care_df is None or len(care_df) == 0:
        return []
    timeline = []
    dates = sorted(care_df['date'].unique())
    for d in dates:
        day_records = care_df[care_df['date'] == d].sort_values('caregiver')
        caregivers = day_records['caregiver'].tolist()
        handover_info = []
        for _, row in day_records.iterrows():
            handover_info.append({
                'caregiver': row['caregiver'],
                'handover_note': row.get('handover_note', ''),
                'env_change': row.get('env_change', '无'),
                'temp_event': row.get('temp_event', ''),
            })
        timeline.append({
            'date': d,
            'caregivers': caregivers,
            'handover_info': handover_info,
            'caregiver_count': len(caregivers),
        })
    return timeline


def compute_routine_completion(care_df):
    if care_df is None or len(care_df) == 0 or 'routine_completion_rate' not in care_df.columns:
        return {'overall_rate': 0, 'by_caregiver': {}, 'by_date': [], 'item_frequency': {}}
    overall = care_df['routine_completion_rate'].mean()
    by_caregiver = {}
    for cg in care_df['caregiver'].unique():
        cg_df = care_df[care_df['caregiver'] == cg]
        by_caregiver[cg] = {
            'avg_rate': round(cg_df['routine_completion_rate'].mean(), 1),
            'min_rate': round(cg_df['routine_completion_rate'].min(), 1),
            'max_rate': round(cg_df['routine_completion_rate'].max(), 1),
            'count': len(cg_df),
        }
    by_date = []
    for d in sorted(care_df['date'].unique()):
        day_df = care_df[care_df['date'] == d]
        by_date.append({
            'date': d,
            'avg_rate': round(day_df['routine_completion_rate'].mean(), 1),
            'caregiver_count': len(day_df),
        })
    item_freq = {}
    for items in care_df['routine_items']:
        for item in items:
            item_freq[item] = item_freq.get(item, 0) + 1
    total_records = len(care_df)
    item_freq_pct = {k: round(v / total_records * 100, 1) for k, v in item_freq.items()}
    return {
        'overall_rate': round(overall, 1),
        'by_caregiver': by_caregiver,
        'by_date': by_date,
        'item_frequency': item_freq_pct,
    }


def compute_nw_response_diff(care_df):
    if care_df is None or len(care_df) == 0:
        return {'by_caregiver': {}, 'difference_alerts': []}
    if 'sleep_nw' not in care_df.columns:
        return {'by_caregiver': {}, 'difference_alerts': []}
    by_caregiver = {}
    for cg in care_df['caregiver'].unique():
        cg_df = care_df[care_df['caregiver'] == cg]
        nw_resp_counts = cg_df['nw_response'].value_counts().to_dict()
        avg_nw = cg_df['sleep_nw'].mean() if cg_df['sleep_nw'].notna().any() else np.nan
        by_caregiver[cg] = {
            'avg_nightwakings': round(avg_nw, 2) if pd.notna(avg_nw) else None,
            'nw_response_distribution': nw_resp_counts,
            'primary_response': cg_df['nw_response'].mode().iloc[0] if len(cg_df) > 0 else '未记录',
            'soothing_method_distribution': cg_df['soothing_method'].value_counts().to_dict(),
            'primary_soothing': cg_df['soothing_method'].mode().iloc[0] if len(cg_df) > 0 else '未记录',
            'count': len(cg_df),
        }
    alerts = []
    caregivers = list(by_caregiver.keys())
    nw_values = {cg: by_caregiver[cg]['avg_nightwakings'] for cg in caregivers}
    valid_nw = {k: v for k, v in nw_values.items() if v is not None}
    if len(valid_nw) >= 2:
        max_cg = max(valid_nw, key=valid_nw.get)
        min_cg = min(valid_nw, key=valid_nw.get)
        diff = valid_nw[max_cg] - valid_nw[min_cg]
        if diff >= 1.0:
            alerts.append({
                'type': 'warning',
                'title': f'不同照护人夜醒响应差异显著',
                'detail': f'{max_cg}照护时平均夜醒{valid_nw[max_cg]:.1f}次，'
                          f'{min_cg}照护时仅{valid_nw[min_cg]:.1f}次，'
                          f'差异{diff:.1f}次。'
                          f'{max_cg}主要采用"{by_caregiver[max_cg]["primary_response"]}"，'
                          f'{min_cg}主要采用"{by_caregiver[min_cg]["primary_response"]}"。'
                          f'建议统一安抚策略。',
            })
    soothing_by_cg = {}
    for cg, info in by_caregiver.items():
        soothing_by_cg[cg] = info['primary_soothing']
    unique_soothings = set(soothing_by_cg.values())
    if len(unique_soothings) >= 2 and len(soothing_by_cg) >= 2:
        alerts.append({
            'type': 'info',
            'title': '不同照护人安抚策略存在差异',
            'detail': '各照护人主要安抚方式：' +
                      '；'.join([f'{cg}→{method}' for cg, method in soothing_by_cg.items()]) +
                      '。策略差异可能导致作息波动，建议协商统一。',
        })
    return {
        'by_caregiver': by_caregiver,
        'difference_alerts': alerts,
    }


def compute_intervention_deviation(care_df, intervention_plan=None):
    if care_df is None or len(care_df) == 0:
        return {'deviation_score': 0, 'deviation_details': [], 'alerts': []}
    deviations = []
    alerts = []
    total_checks = 0
    passed_checks = 0
    if 'sleep_bedtime_min' in care_df.columns and 'routine_completion_rate' in care_df.columns:
        for _, row in care_df.iterrows():
            checks = {}
            bedtime_min = row.get('sleep_bedtime_min', np.nan)
            if pd.notna(bedtime_min):
                target_start = -120
                target_end = 0
                in_window = target_start <= bedtime_min <= target_end
                checks['bedtime_in_window'] = in_window
                total_checks += 1
                if in_window:
                    passed_checks += 1
            routine_rate = row.get('routine_completion_rate', 0)
            if routine_rate > 0:
                routine_ok = routine_rate >= 60
                checks['routine_completed'] = routine_ok
                total_checks += 1
                if routine_ok:
                    passed_checks += 1
            nw_resp = row.get('nw_response', '')
            if nw_resp and nw_resp != '未记录':
                recommended = ['延迟响应(3-5分钟)', '声音安抚', '轻拍安抚']
                resp_ok = nw_resp in recommended
                checks['recommended_response'] = resp_ok
                total_checks += 1
                if resp_ok:
                    passed_checks += 1
            if checks:
                deviations.append({
                    'date': row['date'],
                    'caregiver': row['caregiver'],
                    'checks': checks,
                })
    deviation_score = round(passed_checks / max(total_checks, 1) * 100, 1)
    low_routine_days = care_df[care_df['routine_completion_rate'] < 50] if 'routine_completion_rate' in care_df.columns else pd.DataFrame()
    if len(low_routine_days) > 0 and 'sleep_nw' in low_routine_days.columns:
        low_routine_nw = low_routine_days['sleep_nw'].mean()
        high_routine_days = care_df[care_df['routine_completion_rate'] >= 50]
        high_routine_nw = high_routine_days['sleep_nw'].mean() if 'sleep_nw' in high_routine_days.columns and len(high_routine_days) > 0 else np.nan
        if pd.notna(high_routine_nw) and low_routine_nw > high_routine_nw * 1.3:
            alerts.append({
                'type': 'warning',
                'title': '干预计划未执行导致夜醒增加',
                'detail': f'睡前流程完成率<50%的日子，平均夜醒{low_routine_nw:.1f}次，'
                          f'完成率≥50%的日子仅{high_routine_nw:.1f}次。'
                          f'建议严格执行睡前流程。',
            })
    if deviation_score < 60:
        alerts.append({
            'type': 'warning',
            'title': '干预计划执行偏差较大',
            'detail': f'干预计划执行一致性评分仅{deviation_score}分（满分100），'
                      f'多项执行建议未被照护人采纳。建议加强照护人间协调。',
        })
    return {
        'deviation_score': deviation_score,
        'deviation_details': deviations,
        'alerts': alerts,
    }


def compute_consistency_score(care_df):
    if care_df is None or len(care_df) == 0:
        return {'overall': 0, 'routine_score': 0, 'response_score': 0,
                'handover_score': 0, 'level': '数据不足', 'details': ''}
    routine_score = 0
    if 'routine_completion_rate' in care_df.columns:
        routine_score = min(100, care_df['routine_completion_rate'].mean())
    response_score = 50
    if 'nw_response' in care_df.columns and 'caregiver' in care_df.columns:
        resp_variety = care_df.groupby('caregiver')['nw_response'].nunique()
        if len(resp_variety) > 1:
            max_variety = resp_variety.max()
            min_variety = resp_variety.min()
            if max_variety <= 2:
                response_score = 85
            elif max_variety <= 3:
                response_score = 65
            else:
                response_score = 40
        else:
            response_score = 80
        primary_resp = care_df.groupby('caregiver')['nw_response'].agg(lambda x: x.mode().iloc[0] if len(x) > 0 else '')
        if primary_resp.nunique() <= 1:
            response_score = max(response_score, 80)
        elif primary_resp.nunique() >= 3:
            response_score = min(response_score, 50)
    handover_score = 50
    if 'handover_note' in care_df.columns:
        total_days = care_df['date'].nunique()
        multi_cg_days = care_df.groupby('date')['caregiver'].nunique()
        multi_cg_days = multi_cg_days[multi_cg_days > 1]
        if total_days > 0:
            handover_days_pct = len(multi_cg_days) / total_days
            notes_filled = care_df[care_df['handover_note'].str.strip() != ''].shape[0]
            notes_pct = notes_filled / max(len(care_df), 1)
            handover_score = min(100, round(handover_days_pct * 40 + notes_pct * 60, 1))
    overall = round(routine_score * 0.4 + response_score * 0.35 + handover_score * 0.25, 1)
    if overall >= 80:
        level = '高度一致'
        details = '照护人间协作良好，策略统一，交接充分'
    elif overall >= 60:
        level = '较为一致'
        details = '整体协作较好，个别环节存在差异，建议针对性统一'
    elif overall >= 40:
        level = '一般'
        details = '照护人策略差异明显，交接不够充分，建议加强沟通'
    else:
        level = '不一致'
        details = '照护人策略严重不统一，交接缺失，需立即协调'
    return {
        'overall': overall,
        'routine_score': round(routine_score, 1),
        'response_score': round(response_score, 1),
        'handover_score': round(handover_score, 1),
        'level': level,
        'details': details,
    }


def detect_care_patterns(care_df):
    if care_df is None or len(care_df) < 3:
        return [{'type': 'info', 'title': '数据不足', 'detail': '需要至少3天照护记录才能进行模式识别'}]
    patterns = []
    if 'routine_completion_rate' in care_df.columns and 'sleep_nw' in care_df.columns:
        low_routine = care_df[care_df['routine_completion_rate'] < 50]
        high_routine = care_df[care_df['routine_completion_rate'] >= 60]
        if len(low_routine) >= 2 and len(high_routine) >= 2:
            low_nw = low_routine['sleep_nw'].mean()
            high_nw = high_routine['sleep_nw'].mean()
            if pd.notna(low_nw) and pd.notna(high_nw) and low_nw > high_nw * 1.3:
                patterns.append({
                    'type': 'warning',
                    'title': '睡前流程缺项后夜醒增加',
                    'detail': f'睡前流程完成率<50%的日子，平均夜醒{low_nw:.1f}次，'
                              f'完成率≥60%的日子仅{high_nw:.1f}次，'
                              f'增加{(low_nw/max(high_nw, 0.01)-1)*100:.0f}%。'
                              f'建议严格执行完整睡前程序。',
                })
    if 'caregiver' in care_df.columns and 'sleep_nw' in care_df.columns:
        cg_nw = care_df.groupby('caregiver')['sleep_nw'].mean()
        cg_nw = cg_nw.dropna()
        if len(cg_nw) >= 2:
            max_cg = cg_nw.idxmax()
            min_cg = cg_nw.idxmin()
            diff = cg_nw[max_cg] - cg_nw[min_cg]
            if diff >= 1.0:
                max_soothing = care_df[care_df['caregiver'] == max_cg]['soothing_method'].mode()
                min_soothing = care_df[care_df['caregiver'] == min_cg]['soothing_method'].mode()
                max_s = max_soothing.iloc[0] if len(max_soothing) > 0 else '未知'
                min_s = min_soothing.iloc[0] if len(min_soothing) > 0 else '未知'
                patterns.append({
                    'type': 'warning',
                    'title': '不同照护人安抚策略差异导致作息波动',
                    'detail': f'{max_cg}照护时夜醒{cg_nw[max_cg]:.1f}次（主要用"{max_s}"），'
                              f'{min_cg}照护时{cg_nw[min_cg]:.1f}次（主要用"{min_s}"），'
                              f'差异{diff:.1f}次。建议统一为更有效的安抚策略。',
                })
    if 'routine_completion_rate' in care_df.columns and 'sleep_nw' in care_df.columns:
        very_low = care_df[care_df['routine_completion_rate'] < 30]
        if len(very_low) >= 2:
            very_low_nw = very_low['sleep_nw'].mean()
            normal = care_df[care_df['routine_completion_rate'] >= 30]
            normal_nw = normal['sleep_nw'].mean() if len(normal) > 0 else np.nan
            if pd.notna(normal_nw) and very_low_nw > normal_nw * 1.5:
                patterns.append({
                    'type': 'warning',
                    'title': '严重缺项的睡前程序与高夜醒强相关',
                    'detail': f'睡前流程完成率<30%的日子，夜醒高达{very_low_nw:.1f}次，'
                              f'比正常日子({normal_nw:.1f}次)多{(very_low_nw/max(normal_nw,0.01)-1)*100:.0f}%。'
                              f'需确保睡前流程至少完成60%以上。',
                })
    if 'env_change' in care_df.columns and 'sleep_nw' in care_df.columns:
        env_change_df = care_df[care_df['env_change'] != '无']
        no_env_df = care_df[care_df['env_change'] == '无']
        if len(env_change_df) >= 2 and len(no_env_df) >= 2:
            env_nw = env_change_df['sleep_nw'].mean()
            no_env_nw = no_env_df['sleep_nw'].mean()
            if pd.notna(env_nw) and pd.notna(no_env_nw) and env_nw > no_env_nw * 1.3:
                patterns.append({
                    'type': 'info',
                    'title': '环境变动日睡眠受影响',
                    'detail': f'有环境变动的日子平均夜醒{env_nw:.1f}次，'
                              f'无变动日子{no_env_nw:.1f}次。'
                              f'环境变化可能影响睡眠质量。',
                })
    if 'temp_event' in care_df.columns and 'sleep_nw' in care_df.columns:
        event_df = care_df[care_df['temp_event'].str.strip() != '']
        no_event_df = care_df[care_df['temp_event'].str.strip() == '']
        if len(event_df) >= 2 and len(no_event_df) >= 2:
            evt_nw = event_df['sleep_nw'].mean()
            no_evt_nw = no_event_df['sleep_nw'].mean()
            if pd.notna(evt_nw) and pd.notna(no_evt_nw) and evt_nw > no_evt_nw * 1.3:
                patterns.append({
                    'type': 'info',
                    'title': '临时事件影响睡眠',
                    'detail': f'有临时事件记录的日子平均夜醒{evt_nw:.1f}次，'
                              f'无事件日子{no_evt_nw:.1f}次。'
                              f'临时事件可能增加夜醒风险。',
                })
    if not patterns:
        patterns.append({
            'type': 'success',
            'title': '照护协作良好',
            'detail': '当前照护记录未发现显著协作问题，各照护人策略较为一致。',
        })
    return patterns


def compute_care_summary(care_df):
    if care_df is None or len(care_df) == 0:
        return {}
    summary = {
        'total_records': len(care_df),
        'date_range': (
            care_df['date'].min().strftime('%Y-%m-%d'),
            care_df['date'].max().strftime('%Y-%m-%d')
        ),
        'unique_caregivers': care_df['caregiver'].nunique(),
        'caregiver_distribution': care_df['caregiver'].value_counts().to_dict(),
        'avg_routine_rate': round(care_df['routine_completion_rate'].mean(), 1) if 'routine_completion_rate' in care_df.columns else 0,
        'primary_soothing': care_df['soothing_method'].mode().iloc[0] if len(care_df) > 0 else '未记录',
        'primary_nw_response': care_df['nw_response'].mode().iloc[0] if len(care_df) > 0 else '未记录',
        'env_change_days': len(care_df[care_df['env_change'] != '无']) if 'env_change' in care_df.columns else 0,
        'temp_event_days': len(care_df[care_df['temp_event'].str.strip() != '']) if 'temp_event' in care_df.columns else 0,
    }
    return summary
