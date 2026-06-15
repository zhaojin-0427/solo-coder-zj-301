import pandas as pd
import numpy as np
from phase_analyzer import compute_intervention_vs_prediction

# Simulate the scenario that produces -1912.5% and -400.0%
# When actual is worse than baseline but predicted was good
prediction_result = {
    'baseline': {
        'avg_nightwakings': 0.8,
        'avg_total_sleep_hours': 13.1,
        'stability_score': 63.7,
    },
    'predicted': {
        'avg_nightwakings': 0.5,
        'avg_total_sleep_hours': 13.5,
        'stability_score': 69.1,
    }
}

# Simulate actual data that is WORSE than baseline
from io import StringIO
from generate_sample_data import generate_csv
from data_processor import normalize_columns, preprocess_data
from data_quality import analyze_data_quality, get_filtered_df

csv_content = generate_csv()
df = pd.read_csv(StringIO(csv_content))
df = normalize_columns(df)
processed_df = preprocess_data(df)
data_quality_result = analyze_data_quality(processed_df)
filtered_df = get_filtered_df(processed_df, data_quality_result, exclude_anomalies=True)

# Make actual nightwakings worse to simulate regression
df_worse = filtered_df.copy()
df_worse['nightwakings'] = df_worse['nightwakings'] + 2

result = compute_intervention_vs_prediction(df_worse, prediction_result)
print('=== Test: Intervention with worse actual results ===')
for key, data in result.items():
    print(f'  {key}:')
    print(f'    baseline={data["baseline"]}, predicted={data["predicted"]}, actual={data["actual"]}')
    print(f'    achievement_pct={data["achievement_pct"]}%')

# Test: When actual is better than predicted
df_better = filtered_df.copy()
df_better['nightwakings'] = 0

result2 = compute_intervention_vs_prediction(df_better, prediction_result)
print('\n=== Test: Intervention with better actual results ===')
for key, data in result2.items():
    print(f'  {key}:')
    print(f'    baseline={data["baseline"]}, predicted={data["predicted"]}, actual={data["actual"]}')
    print(f'    achievement_pct={data["achievement_pct"]}%')
