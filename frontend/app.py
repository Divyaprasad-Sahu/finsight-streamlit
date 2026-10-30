"""Run: streamlit run frontend/app.py"""
import streamlit as st
import streamlit.components.v1 as components
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import render_dashboard

st.set_page_config(page_title='FinSight · Financial intelligence', page_icon='◈', layout='wide', initial_sidebar_state='collapsed')
st.markdown('''<style>
header[data-testid="stHeader"] {display:none}
.block-container {padding:0!important;max-width:100%!important}
iframe {border:0!important} footer {display:none}
[data-testid="stMetric"] {background:transparent!important}
</style>''', unsafe_allow_html=True)
mode = st.radio('FinSight workspace', ['Live implementation', 'Demo dashboard'], horizontal=True)
if mode == 'Live implementation':
    from live import render_live
    render_live()
    st.stop()
components.html(render_dashboard(), height=1230, scrolling=True)

with st.expander('Analyze your own data · CSV upload'):
    st.caption('Upload a CSV with Date, Close, and Volume columns (at least 30 rows). The model fits this uploaded sample; flags are in-sample diagnostics, not a forecast.')
    upload = st.file_uploader('Market observations', type='csv')
    if upload is not None:
        import pandas as pd
        import numpy as np
        from sklearn.ensemble import IsolationForest
        try:
            frame = pd.read_csv(upload)
            if not {'Date', 'Close', 'Volume'}.issubset(frame.columns):
                raise ValueError('Required columns: Date, Close, Volume.')
            frame['Date'] = pd.to_datetime(frame['Date'], errors='raise')
            frame = frame.sort_values('Date').drop_duplicates('Date')
            for col in ['Close', 'Volume']:
                frame[col] = pd.to_numeric(frame[col], errors='raise')
            if len(frame) < 30 or frame[['Close','Volume']].isna().any().any() or not np.isfinite(frame[['Close','Volume']]).all().all() or (frame[['Close','Volume']] <= 0).any().any():
                raise ValueError('Provide at least 30 unique dates with positive, finite prices and volumes.')
            returns = frame.Close.pct_change().fillna(0) * 100
            features = np.column_stack([returns, abs(returns), np.log(frame.Volume)])
            model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
            frame['Anomaly'] = model.fit_predict(features) == -1
            frame['Decision score'] = model.decision_function(features)
            st.line_chart(frame.set_index('Date')['Close'])
            st.dataframe(frame, use_container_width=True)
            st.download_button('Download scored CSV', frame.to_csv(index=False), 'finsight-analysis.csv', 'text/csv')
        except (ValueError, TypeError, KeyError) as error:
            st.error(str(error))
