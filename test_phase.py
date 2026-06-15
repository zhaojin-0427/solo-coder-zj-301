import pandas as pd
import numpy as np
from io import StringIO
from generate_sample_data import generate_csv
from data_processor import normalize_columns, preprocess_data
from data_quality import analyze_data_quality, get_filtered_df
from phase_analyzer import (generate_phase_options, filter_by_phase,
    compute_phase_metrics, compare_phases, generate_phase_summary,
    compute_intervention_vs_prediction)
from phase_exporter import export_phase_review_to_excel
from prediction_engine import compute_baseline_metrics, compute_intervention_effects, compute_combined_prediction
from intervention_params import get_default_intervention_params

csv_content = generate_csv()
df = pd.read_csv(StringIO(csv_content))
df = normalize_columns(df)
processed_df = preprocess_data(df)
data_quality_result = analyze_data_quality(processed_df)
filtered_df = get_filtered_df(processed_df, data_quality_result, exclude_anomalies=True)

phases = generate_phase_options(filtered_df, '自然周')
print(f'Total phases: {len(phases)}')
sel = phases[:2]
phase_results = []
df_phases_dict = {}
for pc in sel:
    df_p = filter_by_phase(filtered_df, pc['start_date'], pc['end_date'])
    df_phases_dict[pc['name']] = df_p
    pr = compute_phase_metrics(df_p, pc['name'])
    phase_results.append(pr)

comparison = compare_phases(phase_results)
summary = generate_phase_summary(phase_results, comparison)

# Test 1: Excel export
print('\n=== Test 1: Excel Export ===')
try:
    filters_info = {
        '月龄阶段': '全部',
        '喂养方式': '全部',
        '是否长牙': '全部',
        '天气': '全部',
        '日期范围': '全部',
        '排除异常记录': '是'
    }
    report_io = export_phase_review_to_excel(
        phase_results, comparison, summary,
        df_phases_dict, None,
        data_quality_result, filters_info
    )
    print('Excel export SUCCESS')
except Exception as e:
    print(f'Excel export FAILED: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

# Test 2: Intervention vs Prediction
print('\n=== Test 2: Intervention vs Prediction ===')
try:
    baseline = compute_baseline_metrics(filtered_df)
    default_params = get_default_intervention_params(filtered_df,
        {'avg_total_sleep_hours': 10, 'avg_nightwakings': 2},
        {'overall': 50}, [])
    effects = compute_intervention_effects(filtered_df, baseline, default_params)
    prediction = compute_combined_prediction(baseline, effects, default_params)

    inter_comp = compute_intervention_vs_prediction(filtered_df, prediction)
    print(f'Intervention comparison: {inter_comp}')
    for key, data in inter_comp.items():
        print(f'  {key}: achievement_pct = {data.get("achievement_pct")}')
except Exception as e:
    print(f'Intervention test FAILED: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
