import pandas as pd
import numpy as np
from data_processor import minutes_to_time_display


def compute_basic_stats(df):
    if len(df) == 0:
        return {}
    stats = {
        'days_recorded': len(df),
        'date_range': (df['date'].min().strftime('%Y-%m-%d'), 
                       df['date'].max().strftime('%Y-%m-%d')),
        'avg_total_sleep_hours': round(df['total_sleep_hours'].mean(), 1),
        'avg_night_sleep_hours': round(df['night_sleep_hours'].mean(), 1),
        'avg_nap_hours': round(df['nap_hours'].mean(), 1),
        'avg_nightwakings': round(df['nightwakings'].mean(), 2),
        'night_waking_days_pct': round((df['nightwakings'] > 0).mean() * 100, 1),
        'avg_bedtime': minutes_to_time_display(df['bedtime_minutes'].mean()),
        'avg_wakeup': minutes_to_time_display(df['wakeup_minutes'].mean()),
        'avg_naps_count': round(df['naps_count'].mean(), 1),
        'avg_milk_ml': round(df['milk_amount_ml'].mean(), 0) if df['milk_amount_ml'].notna().any() else None,
    }
    return stats


def compute_group_stats(df, group_col, target_cols):
    if group_col not in df.columns or len(df) == 0:
        return pd.DataFrame()
    grouped = df.groupby(group_col)[target_cols].agg([
        'mean', 'std', 'count'
    ]).round(2)
    grouped.columns = [f'{col}_{stat}' for col, stat in grouped.columns]
    grouped = grouped.reset_index()
    return grouped


def compute_stability_score(df):
    if len(df) < 3:
        return {
            'overall': 50,
            'bedtime_stability': 50,
            'wakeup_stability': 50,
            'nap_stability': 50,
            'details': '数据不足（至少需要3天记录）'
        }
    
    bedtime_std = df['bedtime_minutes'].std()
    wakeup_std = df['wakeup_minutes'].std()
    nap_std = df['total_nap_minutes'].std()
    
    def std_to_score(std, max_minutes=120):
        if pd.isna(std):
            return 50
        score = max(0, 100 - (std / max_minutes) * 100)
        return round(score, 1)
    
    bedtime_score = std_to_score(bedtime_std, 120)
    wakeup_score = std_to_score(wakeup_std, 120)
    nap_score = std_to_score(nap_std, 180)
    
    overall = round(bedtime_score * 0.4 + wakeup_score * 0.3 + nap_score * 0.3, 1)
    
    if overall >= 80:
        level = '非常稳定'
        detail = '作息规律，生物钟健康，建议继续保持'
    elif overall >= 60:
        level = '较为稳定'
        detail = '整体规律，个别项目有波动，可针对性调整'
    elif overall >= 40:
        level = '一般'
        detail = '作息波动较大，建议固定入睡和起床时间'
    else:
        level = '不稳定'
        detail = '作息混乱严重，建议尽快建立固定的睡眠程序'
    
    return {
        'overall': overall,
        'level': level,
        'details': detail,
        'bedtime_stability': bedtime_score,
        'wakeup_stability': wakeup_score,
        'nap_stability': nap_score,
        'bedtime_std_minutes': round(bedtime_std, 1) if not pd.isna(bedtime_std) else 0,
        'wakeup_std_minutes': round(wakeup_std, 1) if not pd.isna(wakeup_std) else 0,
    }


def detect_patterns(df):
    patterns = []
    if len(df) < 5:
        return [{'type': 'info', 'title': '数据不足', 
                 'detail': '需要至少5天数据才能进行模式识别'}]
    
    valid = df.dropna(subset=['last_nap_minutes', 'nightwakings', 'bedtime_minutes'])
    if len(valid) >= 5 and valid['last_nap_minutes'].notna().sum() >= 5:
        late_nap = valid[valid['last_nap_minutes'] >= 15 * 60]
        early_nap = valid[valid['last_nap_minutes'] < 15 * 60]
        if len(late_nap) >= 2 and len(early_nap) >= 2:
            late_avg = late_nap['nightwakings'].mean()
            early_avg = early_nap['nightwakings'].mean()
            if late_avg > early_avg * 1.3:
                patterns.append({
                    'type': 'warning',
                    'title': '白天最后一觉过晚导致夜醒增加',
                    'detail': f'15:00后结束小睡的日子，夜醒次数平均{late_avg:.1f}次，'
                              f'比15:00前结束的({early_avg:.1f}次)高出{(late_avg/early_avg-1)*100:.0f}%。'
                              f'建议将最后一觉结束时间控制在15:00前。'
                })
    
    valid_bt = df.dropna(subset=['bedtime_std_7d', 'nightwakings_7d_avg'])
    if len(valid_bt) >= 5:
        high_var = valid_bt[valid_bt['bedtime_std_7d'] >= 60]
        low_var = valid_bt[valid_bt['bedtime_std_7d'] < 60]
        if len(high_var) >= 2 and len(low_var) >= 2:
            high_avg = high_var['nightwakings_7d_avg'].mean()
            low_avg = low_var['nightwakings_7d_avg'].mean()
            
            df_cp = df.copy()
            df_cp['is_early_morning'] = df_cp['nw_period_group'].apply(
                lambda x: 1 if x in ['凌晨(04-06)', '清晨(06+)'] else 0
            )
            high_days = df_cp.iloc[high_var.index]
            low_days = df_cp.iloc[low_var.index]
            if len(high_days) > 0 and len(low_days) > 0:
                high_em_pct = high_days['is_early_morning'].mean() * 100
                low_em_pct = low_days['is_early_morning'].mean() * 100
                if high_em_pct > low_em_pct + 15:
                    patterns.append({
                        'type': 'warning',
                        'title': '入睡时间波动大时凌晨醒来更频繁',
                        'detail': f'入睡时间标准差≥60分钟的时期，凌晨(04-06点)醒来的占比为{high_em_pct:.0f}%，'
                                  f'比稳定时期({low_em_pct:.0f}%)高出{high_em_pct-low_em_pct:.0f}个百分点。'
                                  f'建议固定入睡时间，波动控制在30分钟内。'
                    })
    
    if 'naps_count' in df.columns and 'nightwakings' in df.columns:
        nap_groups = df.groupby('naps_group')['nightwakings'].mean()
        if len(nap_groups) >= 2:
            worst = nap_groups.idxmax()
            best = nap_groups.idxmin()
            if nap_groups[worst] > nap_groups[best] * 1.3 and nap_groups[worst] > 1:
                patterns.append({
                    'type': 'info',
                    'title': f'小睡次数"{worst}"与夜醒较多相关',
                    'detail': f'小睡{worst}时夜醒{nap_groups[worst]:.1f}次，'
                              f'而{best}时仅{nap_groups[best]:.1f}次，'
                              f'可尝试调整白天小睡次数。'
                })
    
    if 'milk_group' in df.columns and 'nightwakings' in df.columns:
        milk_groups = df.groupby('milk_group')['nightwakings'].mean()
        milk_groups = milk_groups.drop('未知', errors='ignore')
        if len(milk_groups) >= 2:
            low_milk = milk_groups[milk_groups.index.str.contains('500ml以下|500-699')]
            high_milk = milk_groups[milk_groups.index.str.contains('700-899|900ml以上')]
            if len(low_milk) > 0 and len(high_milk) > 0:
                if low_milk.mean() > high_milk.mean() * 1.2:
                    patterns.append({
                        'type': 'info',
                        'title': '奶量不足可能关联夜醒',
                        'detail': f'奶量偏低({low_milk.mean():.1f}次夜醒)比奶量充足'
                                  f'({high_milk.mean():.1f}次)夜醒更频繁，'
                                  f'建议关注白天喂养是否充足。'
                    })
    
    if 'teething' in df.columns:
        teething_yes = df[df['teething'] == '是']
        teething_no = df[df['teething'] == '否']
        if len(teething_yes) >= 2 and len(teething_no) >= 2:
            t_avg = teething_yes['nightwakings'].mean()
            n_avg = teething_no['nightwakings'].mean()
            if t_avg > n_avg * 1.3:
                patterns.append({
                    'type': 'warning',
                    'title': '长牙期夜醒明显增加',
                    'detail': f'长牙期平均夜醒{t_avg:.1f}次，比非长牙期({n_avg:.1f}次)增加{(t_avg/n_avg-1)*100:.0f}%，'
                              f'可在睡前给予牙龈按摩缓解不适。'
                })
    
    age_bedtime = df.groupby('bedtime_group')['nightwakings'].mean()
    if len(age_bedtime) >= 2:
        late_bed = age_bedtime[age_bedtime.index.str.contains('晚睡|超晚睡')]
        normal_bed = age_bedtime[age_bedtime.index.str.contains('正常|早睡')]
        if len(late_bed) > 0 and len(normal_bed) > 0:
            if late_bed.mean() > normal_bed.mean() * 1.2:
                patterns.append({
                    'type': 'warning',
                    'title': '入睡过晚增加夜醒风险',
                    'detail': f'24:00后入睡的日子平均夜醒{late_bed.mean():.1f}次，'
                              f'比正常时段({normal_bed.mean():.1f}次)更多。'
                              f'建议22:00前准备入睡程序。'
                })
    
    if len(patterns) == 0:
        patterns.append({
            'type': 'success',
            'title': '未发现显著不良模式',
            'detail': '当前数据中未检测到明确的作息问题，继续保持良好的睡眠习惯即可。'
        })
    
    return patterns


def compute_correlations(df):
    numeric_cols = ['age_months', 'bedtime_minutes', 'naps_count', 
                    'total_nap_minutes', 'milk_amount_ml', 'nightwakings',
                    'night_sleep_minutes', 'total_sleep_minutes']
    available = [c for c in numeric_cols if c in df.columns and df[c].notna().sum() >= 5]
    if len(available) < 2:
        return pd.DataFrame()
    corr = df[available].corr()
    return corr.round(3)


def age_based_sleep_norms():
    return {
        '0-2月 (新生儿)': {'total': (14, 17), 'night': (8, 10), 'naps': (4, 5)},
        '3-5月 (婴儿早期)': {'total': (12, 15), 'night': (10, 12), 'naps': (3, 4)},
        '6-8月 (婴儿中期)': {'total': (12, 14), 'night': (10, 12), 'naps': (2, 3)},
        '9-11月 (婴儿晚期)': {'total': (11, 14), 'night': (10, 12), 'naps': (2, 3)},
        '12-17月 (幼儿早期)': {'total': (11, 14), 'night': (10, 11), 'naps': (1, 2)},
        '18-23月 (幼儿中期)': {'total': (11, 13), 'night': (10, 11), 'naps': (1, 2)},
        '24月+ (幼儿晚期)': {'total': (10, 13), 'night': (10, 11), 'naps': (1, 1)},
    }


def compare_to_norms(age_group, avg_total, avg_night, avg_naps):
    norms = age_based_sleep_norms()
    if age_group not in norms:
        return []
    n = norms[age_group]
    results = []
    
    def assess(val, low, high, label, unit='小时'):
        if val is None or pd.isna(val):
            return None
        if val < low:
            return ('偏低', f'{label}{val:.1f}{unit}，低于推荐({low}-{high}{unit})')
        elif val > high:
            return ('偏高', f'{label}{val:.1f}{unit}，高于推荐({low}-{high}{unit})')
        else:
            return ('正常', f'{label}{val:.1f}{unit}，符合推荐范围({low}-{high}{unit})')
    
    r = assess(avg_total, n['total'][0], n['total'][1], '总睡眠')
    if r: results.append(('总睡眠', r[0], r[1]))
    
    r = assess(avg_night, n['night'][0], n['night'][1], '夜间睡眠')
    if r: results.append(('夜间睡眠', r[0], r[1]))
    
    r = assess(avg_naps, n['naps'][0], n['naps'][1], '白天小睡', unit='次')
    if r: results.append(('白天小睡', r[0], r[1]))
    
    return results
