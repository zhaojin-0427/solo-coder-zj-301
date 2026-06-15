import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io

CARE_COLUMNS = {
    'date': ['日期', 'date', 'Date', '记录日期'],
    'caregiver': ['照护人', 'caregiver', '主要照护人'],
    'bedtime_routine': ['睡前流程执行', 'bedtime_routine', '睡前程序'],
    'soothing_method': ['安抚方式', 'soothing_method', '安抚策略'],
    'nw_response': ['夜醒响应方式', 'nw_response', '夜醒响应'],
    'env_change': ['环境变动', 'env_change', '环境变化'],
    'temp_event': ['临时事件备注', 'temp_event', '临时事件', '备注'],
    'handover_note': ['交接备注', 'handover_note', '交接说明'],
}

BEDTIME_ROUTINE_ITEMS = [
    '洗澡', '抚触按摩', '换睡衣', '喂奶/喝奶', '读绘本',
    '唱摇篮曲', '调暗灯光', '播放白噪音', '拥抱安抚', '睡前仪式'
]

SOOTHING_METHODS = [
    '抱哄入睡', '轻拍安抚', '声音安抚', '奶睡', '自主入睡', '摇晃安抚', '陪伴入睡'
]

NW_RESPONSES = [
    '立即抱起', '延迟响应(3-5分钟)', '延迟响应(5-10分钟)', '声音安抚',
    '轻拍安抚', '喂奶安抚', '陪伴等待', '不干预'
]

CAREGIVER_TYPES = ['妈妈', '爸爸', '老人', '保姆']

CARE_COLUMN_ALIASES = {}
for canonical, aliases in CARE_COLUMNS.items():
    for alias in aliases:
        CARE_COLUMN_ALIASES[alias.lower()] = canonical


def normalize_care_columns(df):
    df = df.copy()
    new_cols = {}
    for col in df.columns:
        col_lower = str(col).strip().lower()
        if col_lower in CARE_COLUMN_ALIASES:
            new_cols[col] = CARE_COLUMN_ALIASES[col_lower]
        else:
            new_cols[col] = col
    df = df.rename(columns=new_cols)
    return df


def load_care_csv(uploaded_file):
    if uploaded_file is None:
        return None, "请上传照护记录CSV文件"
    try:
        content = uploaded_file.getvalue().decode('utf-8-sig')
        df = pd.read_csv(io.StringIO(content))
        df = normalize_care_columns(df)
        if 'date' not in df.columns:
            return None, "缺少必要列: 日期"
        return df, None
    except Exception as e:
        return None, f"读取照护CSV失败: {str(e)}"


def preprocess_care_data(df, sleep_df=None):
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df = df.sort_values('date').reset_index(drop=True)

    if 'caregiver' not in df.columns:
        df['caregiver'] = '未指定'
    df['caregiver'] = df['caregiver'].fillna('未指定').astype(str)
    df['caregiver'] = df['caregiver'].apply(lambda x: x.strip() if x.strip() in CAREGIVER_TYPES else x.strip())

    if 'bedtime_routine' not in df.columns:
        df['bedtime_routine'] = ''
    df['bedtime_routine'] = df['bedtime_routine'].fillna('').astype(str)
    df['routine_items'] = df['bedtime_routine'].apply(_parse_routine_items)
    df['routine_completed_count'] = df['routine_items'].apply(len)
    df['routine_completion_rate'] = df['routine_completed_count'].apply(
        lambda x: round(x / len(BEDTIME_ROUTINE_ITEMS) * 100, 1) if len(BEDTIME_ROUTINE_ITEMS) > 0 else 0
    )

    if 'soothing_method' not in df.columns:
        df['soothing_method'] = '未记录'
    df['soothing_method'] = df['soothing_method'].fillna('未记录').astype(str)

    if 'nw_response' not in df.columns:
        df['nw_response'] = '未记录'
    df['nw_response'] = df['nw_response'].fillna('未记录').astype(str)

    if 'env_change' not in df.columns:
        df['env_change'] = '无'
    df['env_change'] = df['env_change'].fillna('无').astype(str)

    if 'temp_event' not in df.columns:
        df['temp_event'] = ''
    df['temp_event'] = df['temp_event'].fillna('').astype(str)

    if 'handover_note' not in df.columns:
        df['handover_note'] = ''
    df['handover_note'] = df['handover_note'].fillna('').astype(str)

    if sleep_df is not None:
        sleep_dates = sleep_df[['date', 'nightwakings', 'night_sleep_hours',
                                'total_sleep_hours', 'bedtime_minutes', 'age_group',
                                'feeding_type', 'teething', 'weather']].copy()
        sleep_dates = sleep_dates.rename(columns={
            'nightwakings': 'sleep_nw',
            'night_sleep_hours': 'sleep_night_h',
            'total_sleep_hours': 'sleep_total_h',
            'bedtime_minutes': 'sleep_bedtime_min'
        })
        df = df.merge(sleep_dates, on='date', how='left')

    return df


def _parse_routine_items(routine_str):
    if not routine_str or pd.isna(routine_str) or routine_str.strip() == '':
        return []
    items = []
    for part in routine_str.replace('，', ',').replace('、', ',').replace('/', ',').split(','):
        part = part.strip()
        if part:
            items.append(part)
    return items


def create_care_record(date, caregiver, bedtime_routine='', soothing_method='',
                       nw_response='', env_change='无', temp_event='', handover_note=''):
    return {
        'date': pd.to_datetime(date),
        'caregiver': caregiver,
        'bedtime_routine': bedtime_routine,
        'routine_items': _parse_routine_items(bedtime_routine),
        'routine_completed_count': len(_parse_routine_items(bedtime_routine)),
        'routine_completion_rate': round(len(_parse_routine_items(bedtime_routine)) / len(BEDTIME_ROUTINE_ITEMS) * 100, 1),
        'soothing_method': soothing_method,
        'nw_response': nw_response,
        'env_change': env_change,
        'temp_event': temp_event,
        'handover_note': handover_note,
    }


def add_care_records_to_df(existing_df, new_records):
    if not new_records:
        return existing_df
    new_df = pd.DataFrame(new_records)
    if existing_df is None or len(existing_df) == 0:
        return new_df
    combined = pd.concat([existing_df, new_df], ignore_index=True)
    combined = combined.sort_values('date').reset_index(drop=True)
    combined = combined.drop_duplicates(subset=['date', 'caregiver'], keep='last')
    return combined


def generate_sample_care_data(sleep_df):
    if sleep_df is None or len(sleep_df) == 0:
        return pd.DataFrame()

    import random
    random.seed(42)

    caregivers = CAREGIVER_TYPES
    records = []

    for _, row in sleep_df.iterrows():
        date = row['date']
        n_caregivers = random.randint(1, 3)
        day_caregivers = random.sample(caregivers, n_caregivers)

        for i, cg in enumerate(day_caregivers):
            n_items = random.randint(3, len(BEDTIME_ROUTINE_ITEMS))
            routine_items = random.sample(BEDTIME_ROUTINE_ITEMS, n_items)
            bedtime_routine = ','.join(routine_items)

            soothing = random.choice(SOOTHING_METHODS)
            if cg == '保姆':
                soothing = random.choice(['轻拍安抚', '声音安抚', '陪伴入睡'])
            elif cg == '爸爸':
                soothing = random.choice(['轻拍安抚', '摇晃安抚', '声音安抚', '自主入睡'])

            nw_resp = random.choice(NW_RESPONSES)
            if cg == '老人':
                nw_resp = random.choice(['立即抱起', '喂奶安抚', '陪伴等待'])
            elif cg == '爸爸':
                nw_resp = random.choice(['延迟响应(3-5分钟)', '声音安抚', '轻拍安抚'])

            env = random.choice(['无'] * 8 + ['温度变化', '噪音干扰', '出差/换环境', '换床/换房间'])
            temp_event = ''
            if random.random() < 0.15:
                temp_event = random.choice([
                    '白天兴奋活动多', '打疫苗', '感冒初愈', '换新奶粉',
                    '搬家过渡期', '家庭聚会', '旅行中'
                ])

            handover_note = ''
            if i > 0:
                handover_note = random.choice([
                    '', '', '',
                    '下午小睡推迟30分钟', '晚餐吃了新食物',
                    '白天情绪较好', '有些闹觉', '已喂完睡前奶',
                    '洗澡时情绪稳定', '今天运动量较大'
                ])

            records.append(create_care_record(
                date=date, caregiver=cg,
                bedtime_routine=bedtime_routine,
                soothing_method=soothing,
                nw_response=nw_resp,
                env_change=env,
                temp_event=temp_event,
                handover_note=handover_note
            ))

    df = pd.DataFrame(records)
    sleep_subset = sleep_df[['date', 'nightwakings', 'night_sleep_hours',
                              'total_sleep_hours', 'bedtime_minutes', 'age_group',
                              'feeding_type', 'teething', 'weather']].copy()
    sleep_subset = sleep_subset.rename(columns={
        'nightwakings': 'sleep_nw',
        'night_sleep_hours': 'sleep_night_h',
        'total_sleep_hours': 'sleep_total_h',
        'bedtime_minutes': 'sleep_bedtime_min'
    })
    df = df.merge(sleep_subset, on='date', how='left')
    return df


def filter_care_data(df, caregiver=None, age_group=None, feeding_type=None,
                     teething=None, weather=None, date_range=None,
                     exclude_anomalies=True):
    filtered = df.copy()
    if caregiver and caregiver != '全部':
        filtered = filtered[filtered['caregiver'] == caregiver]
    if age_group and age_group != '全部' and 'age_group' in filtered.columns:
        filtered = filtered[filtered['age_group'] == age_group]
    if feeding_type and feeding_type != '全部' and 'feeding_type' in filtered.columns:
        filtered = filtered[filtered['feeding_type'] == feeding_type]
    if teething and teething != '全部' and 'teething' in filtered.columns:
        filtered = filtered[filtered['teething'] == teething]
    if weather and weather != '全部' and 'weather' in filtered.columns:
        filtered = filtered[filtered['weather'] == weather]
    if date_range and len(date_range) == 2:
        start, end = date_range
        if start:
            filtered = filtered[filtered['date'] >= pd.to_datetime(start)]
        if end:
            filtered = filtered[filtered['date'] <= pd.to_datetime(end)]
    if exclude_anomalies and 'sleep_night_h' in filtered.columns:
        filtered = filtered[
            filtered['sleep_night_h'].notna() &
            (filtered['sleep_night_h'] >= 5) &
            (filtered['sleep_night_h'] <= 15)
        ]
    return filtered.reset_index(drop=True)
