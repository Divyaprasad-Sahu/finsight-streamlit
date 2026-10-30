"""Reproducible local ML demonstration; all market inputs are synthetic."""
from functools import lru_cache
import json
from pathlib import Path
import numpy as np
from sklearn.ensemble import IsolationForest


@lru_cache(maxsize=1)
def dashboard_data():
    rng = np.random.default_rng(42)
    stocks = []
    for symbol, name, price, color in [
        ('AAPL', 'Apple Inc.', 225.50, '#b8e880'),
        ('MSFT', 'Microsoft Corp.', 424.60, '#a9b8fb'),
        ('NVDA', 'NVIDIA Corp.', 132.80, '#e8c88a'),
        ('AMZN', 'Amazon.com Inc.', 192.30, '#8acfc4'),
        ('TSLA', 'Tesla Inc.', 251.40, '#eaa4a4'),
        ('JPM', 'JPMorgan Chase', 221.10, '#b9a5db'),
    ]:
        returns = rng.normal(0.05, 1.0, 120)
        returns[92] = -5.8
        returns[111] = 4.9
        prices = price * np.cumprod(1 + returns / 100)
        volume = rng.lognormal(17.5, 0.4, 120)
        features = np.column_stack([returns, np.abs(returns), np.log(volume)])
        model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        flags = model.fit_predict(features)
        scores = model.decision_function(features)
        stocks.append(dict(symbol=symbol, name=name, color=color,
            prices=np.round(prices, 2).tolist(), returns=np.round(returns, 2).tolist(),
            change=round(float((prices[-1] / prices[-2] - 1) * 100), 2),
            price=round(float(prices[-1]), 2),
            anomaly_count=int((flags == -1).sum()),
            anomalies=np.where(flags == -1)[0].tolist(),
            scores=np.round(scores, 4).tolist()))
    return {'stocks': stocks, 'source': 'Seeded synthetic market data',
            'model': 'Isolation Forest', 'version': 'demo-1',
            'observations': 720, 'features': ['return_pct', 'abs_return_pct', 'log_volume']}


def render_dashboard():
    template = Path(__file__).with_name('dashboard.html').read_text(encoding='utf-8')
    return template.replace('__DASHBOARD_DATA__', json.dumps(dashboard_data()))
