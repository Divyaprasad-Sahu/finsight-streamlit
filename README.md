# FinSight Streamlit

Live market data, anomaly detection, and a local MLOps stack.

Based on https://github.com/koutilyaY/finsight-ai (MIT).

Run: pip install -r frontend/requirements.txt, then streamlit run frontend/app.py.

Streamlit Community Cloud entry point: **frontend/app.py** on **main**, Python 3.11.

See [the implementation guide](frontend/README.md) for Docker, CI/CD, monitoring, and optional local Terraform/Kubernetes.

The live view polls completed Yahoo Finance five-minute bars every 60 seconds. Data may be delayed. Scores are anomaly diagnostics, not forecasts.
