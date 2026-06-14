import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io
import warnings
warnings.filterwarnings('ignore')

from data_quality import (
    smart_parse_time, smart_parse_numeric,
    check_nightwakings_valid as quality_check_nw
)


REQUIRED_COLUMNS = {
    'date': ['日期', 'date', 'Date', '记录日期'],
    'age_months': ['月龄', 'age_months', 'age', '宝宝月龄'],
    'bedtime': ['入睡时间', 'bedtime', 'sleep_time', '晚上入睡时间'],
    'wakeup_time': ['起床时间', 'wakeup_time', 'wake_time', '早上起床时间'],
    'nightwakings': ['夜醒次数', 'nightwakings', 'night_wakings', '夜醒'],
    'naps_count': ['白天小睡次数', 'naps_count', 'naps', '小睡次数'],
    'total_nap_minutes': ['白天小睡总时长(分钟)', 'total_nap_minutes', 'nap_duration', '小睡总时长'],
    'milk_amount_ml': ['奶量(ml)', 'milk_amount_ml', 'milk', '总奶量'],
    'feeding_type': ['喂养方式', 'feeding_type', 'feeding', '喂养'],
    'teething': ['是否长牙', 'teething', '长牙'],
    'weather': ['天气', 'weather', '天气情况']
}

COLUMN_ALIASES = {}
for canonical, aliases in REQUIRED_COLUMNS.items():
    for alias in aliases:
        COLUMN_ALIASES[alias.lower()] = canonical


def normalize_columns(df):
    df = df.copy()
    new_cols = {}
    for col in df.columns:
        col_lower = str(col).strip().lower()
        if col_lower in COLUMN_ALIASES:
            new_cols[col] = COLUMN_ALIASES[col_lower]
        else:
            new_cols[col] = col
    df = df.rename(columns=new_cols)
    return df


def parse_time_to_minutes(time_str):
    if pd.isna(time_str) or time_str == '':
        return np.nan
    try:
        if isinstance(time_str, (int, float)):
            h = float(time_str)
            if h < 0:
                return int(h)
            if h > 24:
                return int(h)
            if h >= 20:
                return int((h - 24) * 60)
            return int(h * 60)
        time_str = str(time_str).strip()
        if ':' in time_str:
            parts = time_str.split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            if h >= 20:
                return (h - 24) * 60 + m
            return h * 60 + m
        else:
            h = float(time_str)
            if h >= 20:
                return int((h - 24) * 60)
            return int(h * 60)
    except:
        return np.nan


def minutes_to_time_display(minutes):
    if pd.isna(minutes):
        return ''
    total = int(minutes) % 1440
    h = total // 60
    m = total % 60
    return f"{h:02d}:{m:02d}"


def parse_date(date_val):
    if pd.isna(date_val):
        return pd.NaT
    try:
        return pd.to_datetime(date_val)
    except:
        try:
            return pd.to_datetime(str(date_val), errors='coerce')
        except:
            return pd.NaT


def categorize_age(months):
    if pd.isna(months):
        return '未知'
    months = float(months)
    if months < 3:
        return '0-2月 (新生儿)'
    elif months < 6:
        return '3-5月 (婴儿早期)'
    elif months < 9:
        return '6-8月 (婴儿中期)'
    elif months < 12:
        return '9-11月 (婴儿晚期)'
    elif months < 18:
        return '12-17月 (幼儿早期)'
    elif months < 24:
        return '18-23月 (幼儿中期)'
    else:
        return '24月+ (幼儿晚期)'


def categorize_bedtime(minutes):
    if pd.isna(minutes):
        return '未知'
    if minutes < -240:
        return '19:00前 (超早睡)'
    elif minutes < -120:
        return '19:00-20:59 (早睡)'
    elif minutes < 0:
        return '21:00-23:59 (正常)'
    elif minutes < 120:
        return '00:00-01:59 (晚睡)'
    else:
        return '02:00后 (超晚睡)'


def categorize_naps_count(n):
    if pd.isna(n):
        return '未知'
    n = int(n)
    if n <= 1:
        return '1次及以下'
    elif n == 2:
        return '2次'
    elif n == 3:
        return '3次'
    else:
        return '4次及以上'


def categorize_milk(ml):
    if pd.isna(ml):
        return '未知'
    ml = float(ml)
    if ml < 500:
        return '500ml以下'
    elif ml < 700:
        return '500-699ml'
    elif ml < 900:
        return '700-899ml'
    else:
        return '900ml以上'


def categorize_nightwaking_period(nw_str):
    if pd.isna(nw_str) or nw_str == '' or nw_str == '无':
        return '无夜醒'
    try:
        periods = get_all_nw_periods(nw_str)
        if not periods:
            return '无夜醒'
        priority_order = ['凌晨(04-06)', '深夜(01-04)', '清晨(06+)', '入睡后(22-01)']
        for p in priority_order:
            if p in periods:
                return p
        return periods[0]
    except:
        return '无夜醒'


def get_all_nw_periods(nw_str):
    if pd.isna(nw_str) or nw_str == '' or nw_str == '无':
        return []
    try:
        nw_str = str(nw_str)
        periods = []
        for t in nw_str.replace('，', ',').split(','):
            t = t.strip()
            if not t:
                continue
            if ':' in t:
                parts = t.split(':')
                h = int(parts[0])
            else:
                try:
                    h = int(float(t))
                except:
                    continue
            if 22 <= h or h < 1:
                periods.append('入睡后(22-01)')
            elif 1 <= h < 4:
                periods.append('深夜(01-04)')
            elif 4 <= h < 6:
                periods.append('凌晨(04-06)')
            elif h >= 6:
                periods.append('清晨(06+)')
        return periods
    except:
        return []


def load_csv(uploaded_file):
    if uploaded_file is None:
        return None, "请上传CSV文件"
    try:
        content = uploaded_file.getvalue().decode('utf-8-sig')
        df = pd.read_csv(io.StringIO(content))
        df = normalize_columns(df)
        missing = [c for c in ['date', 'age_months', 'bedtime', 'wakeup_time', 'nightwakings']
                   if c not in df.columns]
        if missing:
            return None, f"缺少必要列: {', '.join(missing)}"
        return df, None
    except Exception as e:
        return None, f"读取CSV失败: {str(e)}"


def preprocess_data(df):
    df = df.copy()
    df['date'] = df['date'].apply(parse_date)
    df = df.dropna(subset=['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    df['age_months'] = pd.to_numeric(df['age_months'], errors='coerce')
    
    _quality_fixes = []
    
    bt_results = df['bedtime'].apply(smart_parse_time)
    df['bedtime_minutes'] = bt_results.apply(lambda x: x[0])
    df['bedtime_fixed'] = bt_results.apply(lambda x: x[1])
    df['bedtime_fix_note'] = bt_results.apply(lambda x: x[3])
    
    wt_results = df['wakeup_time'].apply(smart_parse_time)
    df['wakeup_minutes'] = wt_results.apply(lambda x: x[0])
    df['wakeup_fixed'] = wt_results.apply(lambda x: x[1])
    df['wakeup_fix_note'] = wt_results.apply(lambda x: x[3])
    
    nw_results = df['nightwakings'].apply(lambda x: smart_parse_numeric(x, 'nightwakings'))
    df['nightwakings'] = nw_results.apply(lambda x: x[0] if pd.notna(x[0]) else 0)
    df['nightwakings_fixed'] = nw_results.apply(lambda x: x[1])
    df['nightwakings_fix_note'] = nw_results.apply(lambda x: x[3])
    
    def calc_night_sleep(row):
        if pd.isna(row['bedtime_minutes']) or pd.isna(row['wakeup_minutes']):
            return np.nan
        bt = row['bedtime_minutes']
        wt = row['wakeup_minutes']
        if wt < bt:
            wt += 24 * 60
        return wt - bt
    
    df['night_sleep_minutes'] = df.apply(calc_night_sleep, axis=1)
    
    if 'total_nap_minutes' in df.columns:
        nap_results = df['total_nap_minutes'].apply(lambda x: smart_parse_numeric(x, 'total_nap_minutes'))
        df['total_nap_minutes'] = nap_results.apply(lambda x: x[0] if pd.notna(x[0]) else 0)
        df['nap_fixed'] = nap_results.apply(lambda x: x[1])
        df['nap_fix_note'] = nap_results.apply(lambda x: x[3])
    else:
        df['total_nap_minutes'] = 0
        df['nap_fixed'] = False
        df['nap_fix_note'] = ''
    
    if 'naps_count' in df.columns:
        naps_results = df['naps_count'].apply(lambda x: smart_parse_numeric(x, 'naps_count'))
        df['naps_count'] = naps_results.apply(lambda x: x[0] if pd.notna(x[0]) else 0)
        df['naps_count_fixed'] = naps_results.apply(lambda x: x[1])
        df['naps_count_fix_note'] = naps_results.apply(lambda x: x[3])
    else:
        df['naps_count'] = 0
        df['naps_count_fixed'] = False
        df['naps_count_fix_note'] = ''
    
    if 'milk_amount_ml' in df.columns:
        milk_results = df['milk_amount_ml'].apply(lambda x: smart_parse_numeric(x, 'milk_amount_ml'))
        df['milk_amount_ml'] = milk_results.apply(lambda x: x[0])
        df['milk_fixed'] = milk_results.apply(lambda x: x[1])
        df['milk_fix_note'] = milk_results.apply(lambda x: x[3])
    else:
        df['milk_amount_ml'] = np.nan
        df['milk_fixed'] = False
        df['milk_fix_note'] = ''
    
    if 'feeding_type' not in df.columns:
        df['feeding_type'] = '未知'
    df['feeding_type'] = df['feeding_type'].fillna('未知').astype(str)
    
    if 'teething' not in df.columns:
        df['teething'] = '否'
    df['teething'] = df['teething'].fillna('否').astype(str).apply(
        lambda x: '是' if str(x).lower() in ['是', 'true', 'yes', '1', 'y'] else '否'
    )
    
    if 'weather' not in df.columns:
        df['weather'] = '未知'
    df['weather'] = df['weather'].fillna('未知').astype(str)
    
    if 'nightwaking_periods' not in df.columns:
        if '夜醒时段' in df.columns:
            df['nightwaking_periods'] = df['夜醒时段']
        else:
            df['nightwaking_periods'] = '无'
    df['nightwaking_periods'] = df['nightwaking_periods'].fillna('无')
    
    df['nw_period_fixed'] = False
    df['nw_period_fix_note'] = ''
    
    for idx in range(len(df)):
        nw_count = df.iloc[idx]['nightwakings']
        nw_periods = df.iloc[idx]['nightwaking_periods']
        valid, fixed, note, corrected_count, corrected_periods = quality_check_nw(
            nw_count, nw_periods
        )
        if fixed:
            df.at[idx, 'nightwakings'] = corrected_count
            df.at[idx, 'nightwaking_periods'] = corrected_periods
            df.at[idx, 'nw_period_fixed'] = True
            df.at[idx, 'nw_period_fix_note'] = note
            df.at[idx, 'nightwakings_fixed'] = True
            if df.iloc[idx]['nightwakings_fix_note']:
                df.at[idx, 'nightwakings_fix_note'] = df.iloc[idx]['nightwakings_fix_note'] + '；' + note
            else:
                df.at[idx, 'nightwakings_fix_note'] = note
    
    df['total_sleep_minutes'] = df['night_sleep_minutes'].fillna(0) + df['total_nap_minutes'].fillna(0)
    df['total_sleep_hours'] = df['total_sleep_minutes'] / 60
    df['night_sleep_hours'] = df['night_sleep_minutes'].fillna(0) / 60
    df['nap_hours'] = df['total_nap_minutes'].fillna(0) / 60
    
    df['age_group'] = df['age_months'].apply(categorize_age)
    df['bedtime_group'] = df['bedtime_minutes'].apply(categorize_bedtime)
    df['naps_group'] = df['naps_count'].apply(categorize_naps_count)
    df['milk_group'] = df['milk_amount_ml'].apply(categorize_milk)
    df['nw_period_group'] = df['nightwaking_periods'].apply(categorize_nightwaking_period)
    df['nw_periods_list'] = df['nightwaking_periods'].apply(get_all_nw_periods)
    df['has_early_morning'] = df['nw_periods_list'].apply(
        lambda x: any(p in ['凌晨(04-06)', '清晨(06+)'] for p in x)
    )
    df['has_late_night'] = df['nw_periods_list'].apply(
        lambda x: any(p in ['入睡后(22-01)', '深夜(01-04)'] for p in x)
    )
    
    def get_last_nap_info(row):
        return row.get('last_nap_end', np.nan)
    
    if 'last_nap_end' not in df.columns:
        df['last_nap_end'] = np.nan
    df['last_nap_minutes'] = df['last_nap_end'].apply(parse_time_to_minutes)
    
    def calc_bedtime_variability(series, window=7):
        valid = series.dropna()
        if len(valid) < 2:
            return np.nan
        centered = valid.values
        diffs = np.abs(np.diff(centered))
        return np.mean(diffs)
    
    df['bedtime_std_7d'] = df['bedtime_minutes'].rolling(7, min_periods=3).std()
    df['nightwakings_7d_avg'] = df['nightwakings'].rolling(7, min_periods=3).mean()
    
    return df


def check_data_quality(df):
    issues = []
    warnings = []
    info = []
    
    total = len(df)
    
    bedtime_missing = df['bedtime_minutes'].isna().sum()
    if bedtime_missing > 0:
        issues.append(f"入睡时间缺失或格式错误: {bedtime_missing}/{total} 条")
    
    wakeup_missing = df['wakeup_minutes'].isna().sum()
    if wakeup_missing > 0:
        issues.append(f"起床时间缺失或格式错误: {wakeup_missing}/{total} 条")
    
    night_sleep_neg = (df['night_sleep_minutes'].dropna() < 5 * 60).sum()
    if night_sleep_neg > 0:
        issues.append(f"夜间睡眠时长异常(<5小时): {night_sleep_neg}/{total} 条，可能是入睡/起床时间填反或格式错误")
    
    night_sleep_long = (df['night_sleep_minutes'].dropna() > 15 * 60).sum()
    if night_sleep_long > 0:
        warnings.append(f"夜间睡眠时长偏长(>15小时): {night_sleep_long}/{total} 条，请确认数据")
    
    has_nw_periods = df['nw_periods_list'].apply(lambda x: len(x) > 0).sum()
    if has_nw_periods == 0 and df['nightwakings'].sum() > 0:
        warnings.append("有夜醒次数但无夜醒时段数据，热力图和时段分析功能将受限")
    elif has_nw_periods == 0:
        info.append("未提供夜醒时段数据，热力图和时段分析功能不可用")
    
    naps_missing = df['naps_count'].isna().sum()
    if naps_missing > 0:
        info.append(f"小睡次数缺失: {naps_missing}/{total} 条")
    
    return {
        'total_rows': total,
        'issues': issues,
        'warnings': warnings,
        'info': info,
        'bedtime_valid': total - bedtime_missing,
        'wakeup_valid': total - wakeup_missing,
        'has_nw_periods': has_nw_periods > 0
    }


def apply_filters(df, age_group=None, feeding_type=None, teething=None, weather=None,
                  date_range=None):
    filtered = df.copy()
    if age_group and age_group != '全部':
        filtered = filtered[filtered['age_group'] == age_group]
    if feeding_type and feeding_type != '全部':
        filtered = filtered[filtered['feeding_type'] == feeding_type]
    if teething and teething != '全部':
        filtered = filtered[filtered['teething'] == teething]
    if weather and weather != '全部':
        filtered = filtered[filtered['weather'] == weather]
    if date_range and len(date_range) == 2:
        start, end = date_range
        if start:
            filtered = filtered[filtered['date'] >= pd.to_datetime(start)]
        if end:
            filtered = filtered[filtered['date'] <= pd.to_datetime(end)]
    return filtered.reset_index(drop=True)
