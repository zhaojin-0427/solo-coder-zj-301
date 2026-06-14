import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random


def generate_csv(days=45, seed=42):
    np.random.seed(seed)
    random.seed(seed)
    
    start_date = datetime(2025, 4, 1)
    dates = [start_date + timedelta(days=i) for i in range(days)]
    
    base_age = 6.0
    ages = [round(base_age + i / 30, 1) for i in range(days)]
    
    bedtimes = []
    wakeups = []
    nightwakings = []
    nightwaking_periods = []
    naps_counts = []
    naps_durations = []
    last_nap_ends = []
    milk_amounts = []
    feeding_types = []
    teething_flags = []
    weathers = []
    
    for i in range(days):
        age = ages[i]
        weekday = dates[i].weekday()
        is_weekend = weekday >= 5
        is_teething_week = (20 <= i <= 28) or (35 <= i <= 40)
        
        bt_base = -135
        bt_variation = np.random.normal(0, 35)
        if is_weekend:
            bt_variation += 30
        if i > 30:
            bt_variation += 20
        if 10 <= i <= 18:
            bt_variation += 45
        bedtime_min = bt_base + bt_variation
        bedtime_min = max(-300, min(bedtime_min, 180))
        
        if bedtime_min < 0:
            h = 24 + bedtime_min // 60
            m = bedtime_min % 60
        else:
            h = bedtime_min // 60
            m = bedtime_min % 60
        bedtimes.append(f"{int(h):02d}:{int(m):02d}")
        
        sleep_duration = np.random.normal(620, 45)
        if bedtime_min > 0:
            sleep_duration -= 30
        if is_teething_week:
            sleep_duration -= 40
        wakeup_min = bedtime_min + sleep_duration
        if wakeup_min < 0:
            wakeup_min += 24 * 60
        wakeup_h = int(wakeup_min // 60) % 24
        wakeup_m = int(wakeup_min % 60)
        wakeups.append(f"{wakeup_h:02d}:{wakeup_m:02d}")
        
        base_nw = 1.0
        if bedtime_min > 30:
            base_nw += 1.2
        if is_teething_week:
            base_nw += 1.5
        if 10 <= i <= 18:
            base_nw += 0.8
        if i > 30:
            base_nw += 0.5
        
        nw = np.random.poisson(base_nw)
        nightwakings.append(nw)
        
        periods_list = []
        for _ in range(nw):
            r = random.random()
            if r < 0.25:
                periods_list.append("23:30")
            elif r < 0.55:
                periods_list.append("02:15")
            elif r < 0.85:
                periods_list.append("05:00")
            else:
                periods_list.append("06:30")
        nightwaking_periods.append(','.join(periods_list) if periods_list else '无')
        
        if age < 7:
            naps_mean = 3.2
        elif age < 9:
            naps_mean = 2.8
        else:
            naps_mean = 2.3
        
        if is_weekend:
            naps_mean -= 0.3
        
        nc = max(1, int(round(np.random.normal(naps_mean, 0.6))))
        naps_counts.append(nc)
        
        nap_total_mean = nc * 55
        nap_total = int(max(30, np.random.normal(nap_total_mean, 30)))
        
        if nap_total > 360:
            base_nw += 0.5
            nw = min(nw + 1, 8)
            nightwakings[-1] = nw
        
        naps_durations.append(nap_total)
        
        if nc > 0:
            last_nap_h = np.random.normal(15.2, 1.1)
            if i % 5 == 0:
                last_nap_h += 2
            last_nap_h = min(max(last_nap_h, 12), 18)
            last_nap_m = int((last_nap_h % 1) * 60)
            last_nap_ends.append(f"{int(last_nap_h):02d}:{last_nap_m:02d}")
            
            if last_nap_h >= 16:
                new_nw = nightwakings[-1] + 1
                nightwakings[-1] = min(new_nw, 8)
                if len(periods_list) < new_nw:
                    periods_list.append("05:30")
                    nightwaking_periods[-1] = ','.join(periods_list)
        else:
            last_nap_ends.append("")
        
        milk_mean = 750 if age < 8 else 680
        milk = int(np.random.normal(milk_mean, 90))
        milk = max(350, min(milk, 1050))
        
        if milk < 550:
            nightwakings[-1] = min(nightwakings[-1] + 1, 8)
            if len(periods_list) < nightwakings[-1]:
                periods_list.append("03:00")
                nightwaking_periods[-1] = ','.join(periods_list) if periods_list else '无'
        milk_amounts.append(milk)
        
        ft_choice = random.choices(['母乳', '配方奶', '混合'], weights=[0.4, 0.35, 0.25])[0]
        feeding_types.append(ft_choice)
        
        if is_teething_week and i % 3 != 0:
            teething_flags.append('是')
        else:
            teething_flags.append('否')
        
        w_choice = random.choices(['晴', '多云', '阴', '雨', '热', '冷'],
                                  weights=[0.35, 0.25, 0.15, 0.1, 0.1, 0.05])[0]
        weathers.append(w_choice)
    
    df = pd.DataFrame({
        '日期': [d.strftime('%Y-%m-%d') for d in dates],
        '月龄': ages,
        '入睡时间': bedtimes,
        '起床时间': wakeups,
        '夜醒次数': nightwakings,
        '白天小睡次数': naps_counts,
        '白天小睡总时长(分钟)': naps_durations,
        'last_nap_end': last_nap_ends,
        '奶量(ml)': milk_amounts,
        '喂养方式': feeding_types,
        '是否长牙': teething_flags,
        '天气': weathers,
        '夜醒时段': nightwaking_periods,
    })
    
    return df.to_csv(index=False)


if __name__ == '__main__':
    csv_content = generate_csv()
    with open('sample_baby_sleep_data.csv', 'w', encoding='utf-8-sig') as f:
        f.write(csv_content)
    print('✅ 示例数据已生成: sample_baby_sleep_data.csv')
    df_check = pd.read_csv('sample_baby_sleep_data.csv')
    print(f'共 {len(df_check)} 行数据')
    print(df_check.head(3))
