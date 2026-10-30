"""Create local credentials and provision a dashboard; never prints the password."""
from pathlib import Path
import json
import secrets

root = Path(__file__).resolve().parent
env = root / '.env'
if not env.exists():
    env.write_text('GRAFANA_ADMIN_PASSWORD=' + secrets.token_urlsafe(24) + '\n')
items = [
    ('Model training time (seconds)', 'finsight_live_fit_seconds'),
    ('Inference time (seconds)', 'finsight_live_inference_seconds'),
    ('Data fetch time (seconds)', 'finsight_live_fetch_seconds'),
    ('Flagged holdout observations', 'finsight_live_holdout_anomalies'),
    ('Market bar age (minutes)', '(time() - finsight_live_latest_bar_timestamp_seconds) / 60'),
    ('Seconds since successful model run', 'time() - finsight_live_last_success_timestamp_seconds'),
    ('Provider requests', 'finsight_live_fetch_total'),
    ('Provider errors', 'finsight_live_fetch_errors_total'),
    ('Training / holdout rows', 'finsight_live_train_rows or finsight_live_holdout_rows'),
    ('Metrics endpoint available', 'up{job="finsight-live"}'),
]
panels = [dict(id=i+1, type='timeseries', title=title,
    gridPos=dict(x=(i % 2)*12, y=(i // 2)*8, w=12, h=8),
    datasource=dict(type='prometheus', uid='prometheus'),
    targets=[dict(expr=query, refId='A', legendFormat='{{__name__}}')])
    for i, (title, query) in enumerate(items)]
dashboard = dict(uid='finsight-live', title='FinSight Live ML Monitoring',
    schemaVersion=39, version=1, refresh='5s',
    time={'from': 'now-15m', 'to': 'now'}, panels=panels)
(root / 'monitoring/grafana/live-dashboard.json').write_text(json.dumps(dashboard, indent=2))
print('Local monitoring configuration prepared.')
