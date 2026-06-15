import pandas as pd
import numpy as np
from phase_analyzer import compute_intervention_vs_prediction

print("=== 测试干预达成率修复 ===")

test_cases = [
    {
        "name": "完全达成目标",
        "baseline_nw": 2.0, "predicted_nw": 1.0, "actual_nw": 1.0,
        "baseline_sleep": 10.0, "predicted_sleep": 11.0, "actual_sleep": 11.0,
        "baseline_stab": 50, "predicted_stab": 70, "actual_stab": 70,
        "expected_nw": 100.0, "expected_sleep": 100.0, "expected_stab": 100.0
    },
    {
        "name": "超额达成（夜醒减少更多）",
        "baseline_nw": 2.0, "predicted_nw": 1.0, "actual_nw": 0.5,
        "baseline_sleep": 10.0, "predicted_sleep": 11.0, "actual_sleep": 11.5,
        "baseline_stab": 50, "predicted_stab": 70, "actual_stab": 80,
        "expected_nw": 150.0, "expected_sleep": 150.0, "expected_stab": 150.0
    },
    {
        "name": "完全未达成（反而恶化）",
        "baseline_nw": 2.0, "predicted_nw": 1.0, "actual_nw": 3.0,
        "baseline_sleep": 10.0, "predicted_sleep": 11.0, "actual_sleep": 9.0,
        "baseline_stab": 50, "predicted_stab": 70, "actual_stab": 40,
        "expected_nw": 0.0, "expected_sleep": 0.0, "expected_stab": 0.0
    },
    {
        "name": "预测改善极小（接近0），实际改善",
        "baseline_nw": 2.0, "predicted_nw": 1.99, "actual_nw": 1.0,
        "baseline_sleep": 10.0, "predicted_sleep": 10.01, "actual_sleep": 11.0,
        "baseline_stab": 50, "predicted_stab": 50.01, "actual_stab": 70,
        "expected_nw": 100.0, "expected_sleep": 100.0, "expected_stab": 100.0
    },
    {
        "name": "预测改善极小（接近0），实际恶化",
        "baseline_nw": 2.0, "predicted_nw": 1.99, "actual_nw": 3.0,
        "baseline_sleep": 10.0, "predicted_sleep": 10.01, "actual_sleep": 9.0,
        "baseline_stab": 50, "predicted_stab": 50.01, "actual_stab": 40,
        "expected_nw": 0.0, "expected_sleep": 0.0, "expected_stab": 0.0
    },
    {
        "name": "旧代码会产生 -1912.5% 的极端情况",
        "baseline_nw": 2.0, "predicted_nw": 1.92, "actual_nw": 3.5,
        "baseline_sleep": 10.0, "predicted_sleep": 10.05, "actual_sleep": 9.8,
        "baseline_stab": 50, "predicted_stab": 50.8, "actual_stab": 47,
        "expected_nw": 0.0, "expected_sleep": 0.0, "expected_stab": 0.0
    },
]

for tc in test_cases:
    print(f"\n测试用例: {tc['name']}")
    
    prediction_result = {
        'predicted': {
            'avg_nightwakings': tc['predicted_nw'],
            'avg_total_sleep_hours': tc['predicted_sleep'],
            'stability_score': tc['predicted_stab']
        },
        'baseline': {
            'avg_nightwakings': tc['baseline_nw'],
            'avg_total_sleep_hours': tc['baseline_sleep'],
            'stability_score': tc['baseline_stab']
        }
    }
    
    if tc['name'] == '完全达成目标':
        bedtime_vals = [1350, 1355, 1345, 1352, 1348, 1351, 1349, 1353, 1347, 1350]
        wakeup_vals = [420, 425, 415, 422, 418, 421, 419, 423, 417, 420]
        nap_vals = [120, 125, 115, 122, 118, 121, 119, 123, 117, 120]
    elif tc['name'] == '超额达成（夜醒减少更多）':
        bedtime_vals = [1350, 1351, 1349, 1350, 1350, 1351, 1349, 1350, 1350, 1350]
        wakeup_vals = [420, 421, 419, 420, 420, 421, 419, 420, 420, 420]
        nap_vals = [120, 121, 119, 120, 120, 121, 119, 120, 120, 120]
    elif tc['name'] == '完全未达成（反而恶化）':
        bedtime_vals = [1350, 1400, 1300, 1410, 1290, 1420, 1280, 1430, 1270, 1440]
        wakeup_vals = [420, 470, 370, 480, 360, 490, 350, 500, 340, 510]
        nap_vals = [120, 170, 70, 180, 60, 190, 50, 200, 40, 210]
    elif tc['name'] == '预测改善极小（接近0），实际改善':
        bedtime_vals = [1350, 1355, 1345, 1352, 1348, 1351, 1349, 1353, 1347, 1350]
        wakeup_vals = [420, 425, 415, 422, 418, 421, 419, 423, 417, 420]
        nap_vals = [120, 125, 115, 122, 118, 121, 119, 123, 117, 120]
    elif tc['name'] == '预测改善极小（接近0），实际恶化':
        bedtime_vals = [1350, 1400, 1300, 1410, 1290, 1420, 1280, 1430, 1270, 1440]
        wakeup_vals = [420, 470, 370, 480, 360, 490, 350, 500, 340, 510]
        nap_vals = [120, 170, 70, 180, 60, 190, 50, 200, 40, 210]
    else:
        bedtime_vals = [1350, 1400, 1300, 1410, 1290, 1420, 1280, 1430, 1270, 1440]
        wakeup_vals = [420, 470, 370, 480, 360, 490, 350, 500, 340, 510]
        nap_vals = [120, 170, 70, 180, 60, 190, 50, 200, 40, 210]
    
    df_intervention = pd.DataFrame({
        'nightwakings': [tc['actual_nw']] * 10,
        'total_sleep_hours': [tc['actual_sleep']] * 10,
        'bedtime_minutes': bedtime_vals,
        'wakeup_minutes': wakeup_vals,
        'nap_hours': [2.0] * 10,
        'night_sleep_hours': [tc['actual_sleep'] - 2.0] * 10,
        'naps_count': [3] * 10,
        'milk_amount_ml': [750] * 10,
        'total_nap_minutes': nap_vals,
        'bedtime': ['22:30'] * 10,
        'wakeup_time': ['07:00'] * 10,
        'date': pd.date_range('2025-04-23', periods=10)
    })
    
    result = compute_intervention_vs_prediction(df_intervention, prediction_result)
    
    nw_pct = result['nightwakings']['achievement_pct']
    sleep_pct = result['total_sleep_hours']['achievement_pct']
    stab_pct = result['stability_score']['achievement_pct']
    
    print(f"  夜醒改善达成率: {nw_pct}% (预期: {tc['expected_nw']}%) {'✅' if abs(nw_pct - tc['expected_nw']) < 0.1 else '❌'}")
    print(f"  睡眠增长达成率: {sleep_pct}% (预期: {tc['expected_sleep']}%) {'✅' if abs(sleep_pct - tc['expected_sleep']) < 0.1 else '❌'}")
    print(f"  稳定度提升达成率: {stab_pct}% (预期: {tc['expected_stab']}%) {'✅' if abs(stab_pct - tc['expected_stab']) < 0.1 else '❌'}")

print("\n=== 测试完成 ===")
