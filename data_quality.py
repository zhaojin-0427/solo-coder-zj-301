import pandas as pd
import numpy as np
import re
from datetime import datetime


FIELD_LABELS = {
    'date': '日期',
    'age_months': '月龄',
    'bedtime': '入睡时间',
    'wakeup_time': '起床时间',
    'nightwakings': '夜醒次数',
    'naps_count': '小睡次数',
    'total_nap_minutes': '小睡总时长(分钟)',
    'milk_amount_ml': '奶量(ml)',
    'nightwaking_periods': '夜醒时段',
}


SEVERITY_WEIGHTS = {
    'critical': 20,
    'warning': 8,
    'info': 2,
}


def _format_minutes(minutes):
    """将分钟数格式化为 HH:MM 时间显示"""
    if pd.isna(minutes):
        return ''
    total = int(minutes) % 1440
    h = total // 60
    m = total % 60
    return f"{h:02d}:{m:02d}"


def smart_parse_time(time_val):
    """
    智能解析时间格式，支持多种常见格式并自动修正。
    返回 (minutes, is_fixed, original_value, fix_note)
    - minutes: 解析后的分钟数（相对于0点的分钟，20点后为负）
    - is_fixed: 是否经过自动修正
    - original_value: 原始值（字符串形式）
    - fix_note: 修正说明（如果有）
    """
    if pd.isna(time_val) or time_val == '' or str(time_val).strip() == '':
        return np.nan, False, '', '空值'
    
    original = str(time_val).strip()
    is_fixed = False
    fix_note = ''
    
    try:
        if isinstance(time_val, (int, float)) and not isinstance(time_val, bool):
            h = float(time_val)
            minutes = _hours_to_minutes(h)
            if pd.notna(minutes):
                return minutes, False, original, ''
            return np.nan, False, original, '数值超出合理范围'
    except:
        pass
    
    val = original
    
    val_clean = val.replace('：', ':').replace(' ', '')
    
    if val_clean != val:
        is_fixed = True
        fix_note = '修正全角冒号/空格'
        val = val_clean
    
    cn_match = re.match(r'^(\d{1,2})[点时](\d{1,2})?[分]?$', val)
    if cn_match:
        h = int(cn_match.group(1))
        m = int(cn_match.group(2)) if cn_match.group(2) else 0
        if is_fixed:
            fix_note += '；' if fix_note else ''
            fix_note += '中文时间格式转换'
        else:
            is_fixed = True
            fix_note = '中文时间格式转换'
        minutes = _hours_to_minutes(h + m / 60.0)
        return minutes, is_fixed, original, fix_note
    
    if ':' in val:
        try:
            parts = val.split(':')
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            if len(parts) > 2:
                s = int(parts[2])
            else:
                s = 0
            minutes = _hours_to_minutes(h + m / 60.0 + s / 3600.0)
            return minutes, is_fixed, original, fix_note
        except:
            pass
    
    try:
        h = float(val)
        minutes = _hours_to_minutes(h)
        if pd.notna(minutes):
            return minutes, is_fixed, original, fix_note
    except:
        pass
    
    am_pm_match = re.match(r'^(\d{1,2})([:\.](\d{1,2}))?\s*(am|pm|上午|下午)$', val, re.IGNORECASE)
    if am_pm_match:
        h = int(am_pm_match.group(1))
        m = int(am_pm_match.group(3)) if am_pm_match.group(3) else 0
        period = am_pm_match.group(4).lower()
        if period in ['pm', '下午']:
            if h < 12:
                h += 12
        elif period in ['am', '上午']:
            if h == 12:
                h = 0
        is_fixed = True
        if fix_note:
            fix_note += '；12小时制转换'
        else:
            fix_note = '12小时制转换'
        minutes = _hours_to_minutes(h + m / 60.0)
        return minutes, is_fixed, original, fix_note
    
    return np.nan, False, original, '无法解析的时间格式'


def _hours_to_minutes(hours):
    """将小时数转换为分钟数（20点后为负，表示前一天）"""
    if pd.isna(hours):
        return np.nan
    if hours < -3 or hours > 30:
        return np.nan
    if hours >= 20:
        return int((hours - 24) * 60)
    if hours < 0:
        return int(hours * 60)
    return int(hours * 60)


def smart_parse_numeric(val, field_name):
    """
    智能解析数值字段，处理常见格式问题。
    返回 (value, is_fixed, original, fix_note)
    """
    if pd.isna(val) or str(val).strip() == '' or str(val).strip().lower() in ['无', 'n/a', 'null', 'none']:
        if field_name in ['nightwakings', 'naps_count', 'total_nap_minutes']:
            return 0, True, str(val) if pd.notna(val) else '', '空值自动补0'
        return np.nan, False, str(val) if pd.notna(val) else '', '空值'
    
    original = str(val).strip()
    is_fixed = False
    fix_note = ''
    
    cleaned = original.replace(',', '').replace('，', '')
    cleaned = re.sub(r'[^\d\.\-]', '', cleaned)
    
    if cleaned != original and cleaned != '':
        is_fixed = True
        fix_note = '去除非数字字符'
    
    try:
        if cleaned == '':
            if field_name in ['nightwakings', 'naps_count', 'total_nap_minutes']:
                return 0, True, original, '无效数值自动补0'
            return np.nan, False, original, '无法解析的数值'
        value = float(cleaned)
        return value, is_fixed, original, fix_note
    except:
        if field_name in ['nightwakings', 'naps_count', 'total_nap_minutes']:
            return 0, True, original, '无效数值自动补0'
        return np.nan, False, original, '无法解析的数值'


def check_bedtime_valid(minutes):
    """检查入睡时间是否合理（18:00 ~ 次日03:00）"""
    if pd.isna(minutes):
        return False, '缺失或无法解析'
    if minutes < -360:
        return False, '入睡时间过早（早于18:00）'
    if minutes > 180:
        return False, '入睡时间过晚（晚于03:00）'
    return True, ''


def check_wakeup_valid(minutes):
    """检查起床时间是否合理（04:00 ~ 12:00）"""
    if pd.isna(minutes):
        return False, '缺失或无法解析'
    if minutes < 240:
        return False, '起床时间过早（早于04:00）'
    if minutes > 720:
        return False, '起床时间过晚（晚于12:00）'
    return True, ''


def check_night_sleep_valid(bt_min, wt_min):
    """检查夜间睡眠时长是否合理（5 ~ 15小时）"""
    if pd.isna(bt_min) or pd.isna(wt_min):
        return False, np.nan, '入睡或起床时间缺失'
    
    bt = bt_min
    wt = wt_min
    if wt < bt:
        wt += 24 * 60
    
    duration = wt - bt
    
    if duration < 300:
        return False, duration, '夜间睡眠过短（<5小时），可能时间填反或格式错误'
    if duration > 900:
        return False, duration, '夜间睡眠过长（>15小时），需确认数据准确性'
    return True, duration, ''


def check_nightwakings_valid(count, periods_str):
    """
    检查夜醒次数和夜醒时段的一致性。
    返回 (valid, is_fixed, fix_note, corrected_count, corrected_periods)
    """
    count_val = count if pd.notna(count) else 0
    periods_str_val = periods_str if pd.notna(periods_str) else ''
    
    is_fixed = False
    fix_note = ''
    corrected_count = count_val
    corrected_periods = periods_str_val
    
    has_periods = False
    try:
        from data_processor import get_all_nw_periods
        periods = get_all_nw_periods(periods_str_val)
        has_periods = len(periods) > 0
    except:
        periods = []
        has_periods = False
    
    if count_val == 0 and has_periods:
        corrected_count = len(periods)
        is_fixed = True
        fix_note = f'夜醒次数为0但有夜醒时段，自动修正为{corrected_count}次'
    
    if count_val > 0 and (periods_str_val == '' or periods_str_val == '无' or pd.isna(periods_str_val)):
        corrected_periods = '无'
        is_fixed = True
        fix_note = '有夜醒次数但无夜醒时段，时段标记为无（不影响次数统计）'
    
    valid = count_val >= 0
    
    return valid, is_fixed, fix_note, corrected_count, corrected_periods


def check_nap_valid(nap_minutes):
    """检查小睡时长是否合理（0 ~ 8小时）"""
    if pd.isna(nap_minutes):
        return True, ''
    if nap_minutes < 0:
        return False, '小睡时长为负数'
    if nap_minutes > 480:
        return False, '小睡时长过长（>8小时）'
    return True, ''


def check_milk_valid(ml):
    """检查奶量是否合理（0 ~ 2000ml）"""
    if pd.isna(ml):
        return True, ''
    if ml < 0:
        return False, '奶量为负数'
    if ml > 2000:
        return False, '奶量过高（>2000ml），需确认数据准确性'
    return True, ''


def check_date_valid(date_val):
    """检查日期是否有效"""
    if pd.isna(date_val):
        return False, '日期缺失或格式错误'
    try:
        dt = pd.to_datetime(date_val, errors='coerce')
        if pd.isna(dt):
            return False, '日期格式无法解析'
        if dt.year < 2000 or dt.year > 2100:
            return False, '日期年份不在合理范围'
        return True, ''
    except:
        return False, '日期格式错误'


def check_age_valid(age_months):
    """检查月龄是否合理（0 ~ 72个月，即0~6岁）"""
    if pd.isna(age_months):
        return False, '月龄缺失'
    if age_months < 0:
        return False, '月龄为负数'
    if age_months > 72:
        return False, '月龄过大（>6岁）'
    return True, ''


def _get_raw_val(df, idx, field, default=''):
    """安全获取 DataFrame 中某行某列的原始值"""
    try:
        if field in df.columns:
            val = df.iloc[idx][field]
            if pd.isna(val):
                return ''
            return str(val)
        return default
    except:
        return default


def analyze_data_quality(df_processed):
    """
    综合分析数据质量，返回质量评分、异常记录列表、影响说明。
    
    参数:
        df_processed: 预处理后的数据（包含原始列和修正标记列）
        
    返回:
        dict: {
            'score': 质量评分(0-100),
            'level': 等级(优秀/良好/一般/较差/差),
            'total_records': 总记录数,
            'valid_records': 有效记录数,
            'excluded_records': 排除记录数(影响睡眠时长),
            'fixable_count': 可自动修正记录数,
            'issues': 问题汇总,
            'anomaly_records': 异常记录详情列表,
            'summary_fields': 各字段异常统计,
        }
    """
    total = len(df_processed)
    if total == 0:
        return {
            'score': 0,
            'level': '无数据',
            'total_records': 0,
            'valid_records': 0,
            'excluded_records': 0,
            'fixable_count': 0,
            'issues': ['无有效数据'],
            'anomaly_records': [],
            'summary_fields': {},
        }
    
    anomaly_records = []
    issues = []
    summary_fields = {}
    
    for idx in range(total):
        record_issues = []
        record_fixes = []
        is_excluded = False
        is_fixable = False
        affected_fields = []
        
        date_val = df_processed.iloc[idx]['date']
        date_valid, date_msg = check_date_valid(date_val)
        if not date_valid:
            record_issues.append({
                'field': 'date',
                'severity': 'critical',
                'message': date_msg,
                'original': _get_raw_val(df_processed, idx, 'date'),
                'corrected': '',
                'fixable': False,
            })
            is_excluded = True
            affected_fields.append('日期')
        
        age_val = df_processed.iloc[idx].get('age_months', np.nan)
        age_valid, age_msg = check_age_valid(age_val)
        if not age_valid:
            record_issues.append({
                'field': 'age_months',
                'severity': 'warning',
                'message': age_msg,
                'original': _get_raw_val(df_processed, idx, 'age_months'),
                'corrected': '',
                'fixable': False,
            })
            affected_fields.append('月龄')
        
        bt_min = df_processed.iloc[idx].get('bedtime_minutes', np.nan)
        bt_valid, bt_msg = check_bedtime_valid(bt_min)
        if not bt_valid:
            bt_fixed = df_processed.iloc[idx].get('bedtime_fixed', False)
            bt_fix_note = df_processed.iloc[idx].get('bedtime_fix_note', '')
            record_issues.append({
                'field': 'bedtime',
                'severity': 'critical',
                'message': bt_msg,
                'original': _get_raw_val(df_processed, idx, 'bedtime'),
                'corrected': _format_minutes(bt_min) if pd.notna(bt_min) else '',
                'fixable': bt_fixed,
            })
            is_excluded = True
            affected_fields.append('入睡时间')
        
        wt_min = df_processed.iloc[idx].get('wakeup_minutes', np.nan)
        wt_valid, wt_msg = check_wakeup_valid(wt_min)
        if not wt_valid:
            record_issues.append({
                'field': 'wakeup_time',
                'severity': 'critical',
                'message': wt_msg,
                'original': _get_raw_val(df_processed, idx, 'wakeup_time'),
                'corrected': _format_minutes(wt_min) if pd.notna(wt_min) else '',
                'fixable': df_processed.iloc[idx].get('wakeup_fixed', False),
            })
            is_excluded = True
            affected_fields.append('起床时间')
        
        if bt_valid and wt_valid:
            sleep_valid, sleep_dur, sleep_msg = check_night_sleep_valid(bt_min, wt_min)
            if not sleep_valid:
                record_issues.append({
                    'field': 'night_sleep',
                    'severity': 'critical',
                    'message': sleep_msg,
                    'original': f'{_get_raw_val(df_processed, idx, "bedtime")} ~ {_get_raw_val(df_processed, idx, "wakeup_time")}',
                    'corrected': f'{sleep_dur/60:.1f}小时' if pd.notna(sleep_dur) else '',
                    'fixable': False,
                })
                is_excluded = True
                affected_fields.append('夜间睡眠时长')
        
        nw_fixed_flag = df_processed.iloc[idx].get('nightwakings_fixed', False)
        nw_fix_note = df_processed.iloc[idx].get('nightwakings_fix_note', '')
        if nw_fixed_flag and nw_fix_note:
            record_fixes.append({
                'field': 'nightwakings',
                'message': nw_fix_note,
                'original': f'次数:{_get_raw_val(df_processed, idx, "nightwakings")}, 时段:{_get_raw_val(df_processed, idx, "nightwaking_periods")}',
                'corrected': f'次数:{df_processed.iloc[idx].get("nightwakings", 0)}, 时段:{df_processed.iloc[idx].get("nightwaking_periods", "")}',
            })
            is_fixable = True
        
        bt_fixed = df_processed.iloc[idx].get('bedtime_fixed', False)
        bt_fix_note = df_processed.iloc[idx].get('bedtime_fix_note', '')
        if bt_fixed and bt_valid and bt_fix_note:
            record_fixes.append({
                'field': 'bedtime',
                'message': bt_fix_note,
                'original': _get_raw_val(df_processed, idx, 'bedtime'),
                'corrected': _format_minutes(bt_min),
            })
            is_fixable = True
        
        wt_fixed = df_processed.iloc[idx].get('wakeup_fixed', False)
        wt_fix_note = df_processed.iloc[idx].get('wakeup_fix_note', '')
        if wt_fixed and wt_valid and wt_fix_note:
            record_fixes.append({
                'field': 'wakeup_time',
                'message': wt_fix_note,
                'original': _get_raw_val(df_processed, idx, 'wakeup_time'),
                'corrected': _format_minutes(wt_min),
            })
            is_fixable = True
        
        nap_fixed = df_processed.iloc[idx].get('nap_fixed', False)
        nap_fix_note = df_processed.iloc[idx].get('nap_fix_note', '')
        if nap_fixed and nap_fix_note:
            record_fixes.append({
                'field': 'total_nap_minutes',
                'message': nap_fix_note,
                'original': _get_raw_val(df_processed, idx, 'total_nap_minutes'),
                'corrected': str(df_processed.iloc[idx].get('total_nap_minutes', 0)),
            })
            is_fixable = True
        
        naps_count_fixed = df_processed.iloc[idx].get('naps_count_fixed', False)
        naps_count_fix_note = df_processed.iloc[idx].get('naps_count_fix_note', '')
        if naps_count_fixed and naps_count_fix_note:
            record_fixes.append({
                'field': 'naps_count',
                'message': naps_count_fix_note,
                'original': _get_raw_val(df_processed, idx, 'naps_count'),
                'corrected': str(df_processed.iloc[idx].get('naps_count', 0)),
            })
            is_fixable = True
        
        milk_fixed = df_processed.iloc[idx].get('milk_fixed', False)
        milk_fix_note = df_processed.iloc[idx].get('milk_fix_note', '')
        if milk_fixed and milk_fix_note:
            record_fixes.append({
                'field': 'milk_amount_ml',
                'message': milk_fix_note,
                'original': _get_raw_val(df_processed, idx, 'milk_amount_ml'),
                'corrected': str(df_processed.iloc[idx].get('milk_amount_ml', '')),
            })
            is_fixable = True
        
        nap_minutes = df_processed.iloc[idx].get('total_nap_minutes', 0)
        nap_valid, nap_msg = check_nap_valid(nap_minutes)
        if not nap_valid:
            record_issues.append({
                'field': 'total_nap_minutes',
                'severity': 'warning',
                'message': nap_msg,
                'original': _get_raw_val(df_processed, idx, 'total_nap_minutes'),
                'corrected': '',
                'fixable': False,
            })
            affected_fields.append('小睡总时长')
        
        milk_ml = df_processed.iloc[idx].get('milk_amount_ml', np.nan)
        milk_valid, milk_msg = check_milk_valid(milk_ml)
        if not milk_valid:
            record_issues.append({
                'field': 'milk_amount_ml',
                'severity': 'warning',
                'message': milk_msg,
                'original': _get_raw_val(df_processed, idx, 'milk_amount_ml'),
                'corrected': '',
                'fixable': False,
            })
            affected_fields.append('奶量')
        
        if record_issues or record_fixes:
            date_str = df_processed.iloc[idx]['date'].strftime('%Y-%m-%d') if pd.notna(df_processed.iloc[idx]['date']) else '未知日期'
            
            anomaly_records.append({
                'index': idx,
                'date': date_str,
                'issues': record_issues,
                'fixes': record_fixes,
                'is_excluded': is_excluded,
                'is_fixable': is_fixable,
                'affected_fields': affected_fields,
                'severity': 'critical' if any(i['severity'] == 'critical' for i in record_issues) else 
                           'warning' if any(i['severity'] == 'warning' for i in record_issues) else 'info',
            })
    
    field_counts = {}
    for rec in anomaly_records:
        for issue in rec['issues']:
            field = issue['field']
            if field not in field_counts:
                field_counts[field] = {'critical': 0, 'warning': 0, 'info': 0, 'total': 0}
            field_counts[field][issue['severity']] += 1
            field_counts[field]['total'] += 1
    
    for field, counts in field_counts.items():
        label = FIELD_LABELS.get(field, field)
        summary_fields[label] = counts
    
    total_critical = sum(1 for r in anomaly_records if r['severity'] == 'critical')
    total_warning = sum(1 for r in anomaly_records if r['severity'] == 'warning')
    total_fixable = sum(1 for r in anomaly_records if r['is_fixable'])
    total_excluded = sum(1 for r in anomaly_records if r['is_excluded'])
    
    base_score = 100
    
    critical_deduct = min(total_critical * 5, 40)
    warning_deduct = min(total_warning * 2, 20)
    
    base_score -= critical_deduct + warning_deduct
    score = max(0, min(100, int(base_score)))
    
    if score >= 90:
        level = '优秀'
    elif score >= 75:
        level = '良好'
    elif score >= 60:
        level = '一般'
    elif score >= 40:
        level = '较差'
    else:
        level = '差'
    
    if total_critical > 0:
        issues.append(f'{total_critical} 条记录存在严重问题（会导致睡眠时长失真），默认已排除')
    if total_warning > 0:
        issues.append(f'{total_warning} 条记录存在警告级问题')
    if total_fixable > 0:
        issues.append(f'{total_fixable} 条记录已自动修正格式问题')
    
    return {
        'score': score,
        'level': level,
        'total_records': total,
        'valid_records': total - total_excluded,
        'excluded_records': total_excluded,
        'fixable_count': total_fixable,
        'issues': issues,
        'anomaly_records': anomaly_records,
        'summary_fields': summary_fields,
    }


def get_filtered_df(df, quality_result, exclude_anomalies=True):
    """
    根据异常检测结果获取过滤后的 DataFrame。
    
    参数:
        df: 预处理后的 DataFrame
        quality_result: analyze_data_quality 的返回结果
        exclude_anomalies: 是否排除异常记录（默认排除）
        
    返回:
        DataFrame: 过滤后的数据
    """
    if not exclude_anomalies:
        return df.copy()
    
    excluded_indices = [r['index'] for r in quality_result['anomaly_records'] if r['is_excluded']]
    
    if not excluded_indices:
        return df.copy()
    
    filtered = df.drop(index=excluded_indices).reset_index(drop=True)
    return filtered


def get_anomaly_dataframe(quality_result):
    """
    将异常记录转换为 DataFrame，用于导出 Excel。
    
    返回 DataFrame，包含：
    - 日期
    - 字段
    - 原始值
    - 修正值
    - 是否纳入统计
    - 异常原因
    - 影响字段
    - 严重程度
    - 类型（问题/修正）
    """
    rows = []
    
    for rec in quality_result['anomaly_records']:
        date = rec['date']
        is_included = '否' if rec['is_excluded'] else '是'
        affected = '、'.join(rec['affected_fields']) if rec['affected_fields'] else ''
        
        for issue in rec['issues']:
            field_label = FIELD_LABELS.get(issue['field'], issue['field'])
            rows.append({
                '日期': date,
                '类型': '异常',
                '字段': field_label,
                '原始值': str(issue.get('original', '')),
                '修正值': str(issue.get('corrected', '')) if issue.get('corrected') else '',
                '严重程度': issue['severity'],
                '异常原因': issue['message'],
                '是否纳入统计': is_included,
                '影响字段': affected,
            })
        
        for fix in rec['fixes']:
            field_label = FIELD_LABELS.get(fix['field'], fix['field'])
            rows.append({
                '日期': date,
                '类型': '已修正',
                '字段': field_label,
                '原始值': str(fix.get('original', '')),
                '修正值': str(fix.get('corrected', '')),
                '严重程度': 'info',
                '异常原因': fix['message'],
                '是否纳入统计': is_included,
                '影响字段': '',
            })
    
    if not rows:
        return pd.DataFrame(columns=['日期', '类型', '字段', '原始值', '修正值', 
                                      '严重程度', '异常原因', '是否纳入统计', '影响字段'])
    
    return pd.DataFrame(rows)
