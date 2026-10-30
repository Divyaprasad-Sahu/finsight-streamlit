"""Measures this exporter's model run, independently of Streamlit sessions."""
import time
from prometheus_client import Gauge, start_http_server
from model import dashboard_data

fit_seconds = Gauge('finsight_model_fit_seconds', 'Wall time for the six synthetic demo model fits')
observations = Gauge('finsight_observations', 'Synthetic input observations', ['symbol'])
anomalies = Gauge('finsight_anomalies', 'In-sample flagged observations', ['symbol'])
last_fit = Gauge('finsight_model_last_fit_timestamp_seconds', 'Unix timestamp of last successful fit')

if __name__ == '__main__':
    start_http_server(9108)
    while True:
        dashboard_data.cache_clear()
        start = time.perf_counter()
        result = dashboard_data()
        fit_seconds.set(time.perf_counter() - start)
        for stock in result['stocks']:
            observations.labels(stock['symbol']).set(len(stock['prices']))
            anomalies.labels(stock['symbol']).set(stock['anomaly_count'])
        last_fit.set_to_current_time()
        time.sleep(60)
