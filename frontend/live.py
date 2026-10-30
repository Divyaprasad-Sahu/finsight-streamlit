"""Real market bars -> chronological holdout inference -> Streamlit and metrics."""
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
from threading import Lock, Thread
from zoneinfo import ZoneInfo
import time
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import yfinance as yf


class Telemetry:
    def __init__(self):
        self.lock = Lock()
        self.values = {name: 0 for name in [
            'finsight_live_fetch_total', 'finsight_live_fetch_errors_total',
            'finsight_live_fetch_seconds', 'finsight_live_fit_seconds',
            'finsight_live_inference_seconds', 'finsight_live_train_rows',
            'finsight_live_holdout_rows', 'finsight_live_holdout_anomalies',
            'finsight_live_last_success_timestamp_seconds',
            'finsight_live_latest_bar_timestamp_seconds']}

    def update(self, **values):
        with self.lock:
            self.values.update(values)

    def increment(self, name):
        with self.lock:
            self.values[name] += 1

    def exposition(self):
        with self.lock:
            values = dict(self.values)
        return '\n'.join(f'# TYPE {name} {"counter" if name.endswith("_total") else "gauge"}\n{name} {value}'
                         for name, value in values.items()) + '\n'


@st.cache_resource
def telemetry():
    return Telemetry()


@st.cache_resource
def start_metrics():
    state = telemetry()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/metrics':
                self.send_error(404)
                return
            body = state.exposition().encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    try:
        server = ThreadingHTTPServer((os.getenv('FINSIGHT_METRICS_HOST', '127.0.0.1'), 9109), Handler)
        Thread(target=server.serve_forever, daemon=True).start()
        return server, None
    except OSError as error:
        return None, str(error)


@st.cache_data(ttl=55, show_spinner=False)
def fetch_bars(symbol):
    state = telemetry()
    state.increment('finsight_live_fetch_total')
    started = time.perf_counter()
    try:
        cache = Path(os.getenv('FINSIGHT_MARKET_CACHE', str(Path(__file__).resolve().parent / '.market-cache')))
        cache.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache))
        frame = yf.Ticker(symbol).history(period='5d', interval='5m', auto_adjust=True,
                                         timeout=15, raise_errors=True)
        if frame.empty:
            raise ValueError('The provider returned no observations. Try another symbol.')
        frame = frame[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        frame.index = pd.to_datetime(frame.index, utc=True)
        frame = frame[~frame.index.duplicated()].sort_index()
        # Exclude the still-forming five-minute candle.
        frame = frame[frame.index + pd.Timedelta(minutes=5) <= pd.Timestamp.now(tz='UTC')]
        frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
        frame = frame[(frame.Close > 0) & (frame.Volume >= 0)]
        if len(frame) < 150:
            raise ValueError('Fewer than 150 completed bars available; select another symbol.')
        fetched = datetime.now(timezone.utc)
        seconds = time.perf_counter() - started
        state.update(finsight_live_fetch_seconds=seconds)
        return frame, fetched, seconds
    except Exception:
        state.increment('finsight_live_fetch_errors_total')
        raise


def score_bars(frame):
    """Fit on earlier observations only; score the later chronological holdout."""
    features = pd.DataFrame(index=frame.index)
    returns = frame.Close.pct_change() * 100
    features['return_pct'] = returns
    features['absolute_return'] = returns.abs()
    features['log_volume'] = np.log1p(frame.Volume)
    features['rolling_volatility'] = returns.rolling(20).std()
    features = features.replace([np.inf, -np.inf], np.nan).dropna()
    split = int(len(features) * 0.8)
    if split < 100 or len(features) - split < 20:
        raise ValueError('Need at least 100 training rows and 20 holdout rows after feature warm-up.')
    train, holdout = features.iloc[:split], features.iloc[split:]
    estimator = make_pipeline(StandardScaler(), IsolationForest(
        n_estimators=100, contamination=0.05, random_state=42))
    started = time.perf_counter()
    estimator.fit(train)
    fit_seconds = time.perf_counter() - started
    started = time.perf_counter()
    scores = estimator.decision_function(holdout)
    inference_seconds = time.perf_counter() - started
    result = frame.loc[holdout.index].copy()
    result['Return %'] = holdout.return_pct
    result['Decision score'] = scores
    result['Anomaly'] = scores < 0
    return result, train, fit_seconds, inference_seconds


def render_live():
    st.markdown('''<style>
    .block-container{padding:2rem 2.3rem!important;max-width:1400px!important}
    [data-testid="stMetric"]{border:1px solid #82957466;border-radius:12px;padding:18px}
    </style>''', unsafe_allow_html=True)
    st.title('FinSight · Live implementation')
    st.caption('Public market data → features → model fitting → holdout inference → monitoring')
    controls = st.columns([2, 2, 1])
    symbol = controls[0].selectbox('Market symbol', ['BTC-USD', 'ETH-USD', 'AAPL', 'MSFT', 'NVDA', 'RELIANCE.NS'])
    auto = controls[1].toggle('Refresh every 60 seconds', value=True)
    if controls[2].button('Fetch now', use_container_width=True):
        fetch_bars.clear()
    st.info('Source: Yahoo Finance via yfinance · completed 5-minute bars · may be delayed. '
            'Crypto trades around the clock; equities update during their trading session. '
            'This is polling, not an exchange tick stream. No synthetic fallback is used.')
    _, metric_error = start_metrics()
    if metric_error:
        st.warning('Metrics endpoint could not start on port 9109: ' + metric_error)

    @st.fragment(run_every=60 if auto else None)
    def update():
        tick = datetime.now(timezone.utc)
        st.session_state['live_refresh_count'] = st.session_state.get('live_refresh_count', 0) + 1
        with st.status('Fetching market bars and running the model…', expanded=True) as status:
            try:
                frame, fetched, fetch_seconds = fetch_bars(symbol)
                st.write(f'1. Yahoo Finance returned {len(frame):,} completed bars for {symbol}.')
                scored, train, fit_seconds, inference_seconds = score_bars(frame)
                st.write(f'2. Computed four features; fitted on {len(train):,} earlier bars in {fit_seconds:.3f}s.')
                st.write(f'3. Scored {len(scored):,} later, unseen bars in {inference_seconds:.3f}s.')
                st.write('4. Metrics collected in process.' if metric_error else
                         '4. Published actual run counters, timings, and timestamps at port 9109 /metrics.')
                status.update(label='Pipeline complete · real provider data', state='complete', expanded=False)
            except Exception as error:
                status.update(label='Data pipeline failed', state='error', expanded=True)
                st.error(f'{type(error).__name__}: {error}')
                st.caption('No prices or model results have been fabricated. Use Fetch now to retry.')
                return
        latest = scored.iloc[-1]
        last_time = scored.index[-1]
        age = max(0, (datetime.now(timezone.utc) - last_time.to_pydatetime()).total_seconds())
        telemetry().update(
            finsight_live_fit_seconds=fit_seconds, finsight_live_inference_seconds=inference_seconds,
            finsight_live_train_rows=len(train), finsight_live_holdout_rows=len(scored),
            finsight_live_holdout_anomalies=int(scored.Anomaly.sum()),
            finsight_live_last_success_timestamp_seconds=time.time(),
            finsight_live_latest_bar_timestamp_seconds=last_time.timestamp())
        metrics = st.columns(4)
        currency = '₹' if symbol.endswith('.NS') else '$'
        metrics[0].metric(f'{symbol} · latest completed close', f'{currency}{latest.Close:,.2f}', f'{latest["Return %"]:+.3f}% vs previous bar')
        metrics[1].metric('Latest signal', 'ANOMALY' if latest.Anomaly else 'Within range')
        metrics[2].metric('Holdout flags', f'{int(scored.Anomaly.sum())} / {len(scored)}')
        metrics[3].metric('Model fit time', f'{fit_seconds * 1000:.0f} ms')
        st.caption(f'Checked {tick.astimezone(ZoneInfo("Asia/Kolkata")).isoformat(timespec="seconds")} · '
                   f'Fetched {fetched.isoformat(timespec="seconds")} · Last bar starts {last_time.isoformat()} · '
                   f'Bar age {age / 60:.1f} min · Refresh #{st.session_state["live_refresh_count"]}')
        if age > 20 * 60:
            st.warning('The latest available bar is over 20 minutes old. The market may be closed or the provider may be delayed. This is the actual provider timestamp.')
        chart, evidence = st.columns([3, 1])
        with chart:
            st.subheader('Actual market prices · chronological holdout')
            st.line_chart(scored[['Close']], use_container_width=True)
        with evidence:
            st.subheader('Execution evidence')
            st.write(f'Fetch: **{fetch_seconds:.3f}s**')
            st.write(f'Fit: **{fit_seconds:.3f}s**')
            st.write(f'Inference: **{inference_seconds:.3f}s**')
            st.write(f'Training ends: **{train.index[-1]}**')
            st.write(f'Holdout starts: **{scored.index[0]}**')
            st.write(f'Latest score: **{latest["Decision score"]:.4f}**')
        st.caption('The estimator and scaler fit only the first 80% of feature rows. The remaining 20% are scored '
                   'without fitting on them. Negative scores flag unusual behavior; no labeled accuracy or forecasting claim is made.')
        st.subheader('Recent inference results')
        st.dataframe(scored.tail(30).sort_index(ascending=False), use_container_width=True)
        st.download_button('Download real-data inference CSV', scored.to_csv(), f'{symbol}-real-inference.csv', 'text/csv')
        with st.expander('View the implementation and monitoring queries'):
            st.code('''# Actual implementation: frontend/live.py
bars = yf.Ticker(symbol).history(period="5d", interval="5m")
# Remove incomplete candles; engineer returns, volume, volatility.
train, holdout = features.iloc[:split], features.iloc[split:]
model = make_pipeline(StandardScaler(), IsolationForest(random_state=42))
model.fit(train)
scores = model.decision_function(holdout)
# @st.fragment(run_every=60) refreshes this view.
''', language='python')
            st.code(telemetry().exposition(), language='text')
            st.markdown('[yfinance data documentation](https://ranaroussi.github.io/yfinance/reference/yfinance.price_history.html)')
            st.caption('Metrics are process-wide and describe the latest successful run across sessions. '
                       'Fetch counters count provider requests, not cached view refreshes. They reset on restart.')
    update()
