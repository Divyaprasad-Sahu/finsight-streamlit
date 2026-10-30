# FinSight Streamlit frontend

A lightweight implementation built beside the original FinSight AI stack. The default Live implementation view polls real Yahoo Finance five-minute bars every 60 seconds, shows source timestamps and actual model timings, and scores a chronological holdout. The Demo dashboard view retains the explicitly synthetic sample. No AWS, Azure, API keys, Kafka, or LLM required. Original source: https://github.com/koutilyaY/finsight-ai (MIT license retained in the repository).

## Basic deployment

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r frontend/requirements.txt
streamlit run frontend/app.py
```

Open http://localhost:8501. On macOS/Linux, activate with `source .venv/bin/activate`.

The dashboard includes six working pages: Overview, ML models, CI/CD pipeline, Infrastructure, Monitoring, and Implementation. Choose assets, switch chart windows, filter the watchlist, view model results, and download scored CSVs. Expand the native Streamlit uploader below the dashboard to analyze your own Date/Close/Volume CSV (30+ unique dates).

## What the ML actually does

`model.py` generates 120 seeded synthetic price/volume observations for each of six symbols and fits scikit-learn Isolation Forest on return, absolute return, and log volume. These are **in-sample anomaly flags**, not forecasting accuracy, trading advice, live market data, or FinBERT sentiment. The web interface embeds actual Python model outputs. Run analysis opens those computed results; it does not trigger an LLM or start a background training job. The native CSV uploader fits a separate estimator on the uploaded sample, without writing it to disk.

## Docker + Prometheus + Grafana

```powershell
Copy-Item frontend/.env.example frontend/.env
# Edit frontend/.env and choose a Grafana password.
docker compose -f frontend/compose.yml up --build -d
```

Streamlit: http://localhost:8501, Prometheus: http://localhost:9090, Grafana: http://localhost:3000 (admin / your configured password). Grafana loads a dashboard and Prometheus data source automatically. Exporter metrics describe its independent synthetic model fit every 60 seconds, not Streamlit sessions or CSV uploads. All exposed ports bind to localhost. Stop with `docker compose -f frontend/compose.yml down`; named Grafana storage is retained.

## GitHub versioning and CI/CD

The new workflow is in the active `.github/workflows/frontend.yml` directory. Pull requests test the model and build/smoke-test Docker. Main-branch pushes also publish a commit-SHA-tagged image to `ghcr.io/<owner>/<repo>/streamlit:<sha>`. Deploy locally by pulling that tag and running it with `docker run -p 127.0.0.1:8501:8501 <image>`. Publication requires pushing this implementation to a repository you control; no remote changes have been made. Deployment is manual, to keep the setup basic.

## Optional local Terraform

Requires Terraform and a running local Docker daemon. Do not run this and Compose on the same port simultaneously.

```text
cd frontend/terraform
terraform init
terraform plan
terraform apply
```

The kreuzwerker/docker provider builds the Streamlit image and manages a local container. On Windows configure `DOCKER_HOST` for your Docker Desktop daemon if its default endpoint is unavailable. No cloud resources are created. The upstream `mlops/terraform` AWS examples are unchanged and not part of this deployment.

## Optional local Kubernetes

```text
docker build -t finsight-streamlit:local -f frontend/Dockerfile .
kind load docker-image finsight-streamlit:local
kubectl apply -f frontend/k8s.yaml
kubectl port-forward service/finsight-streamlit 8501:8501
```

Use an existing kind cluster, or `minikube image load finsight-streamlit:local` for Minikube. The manifest provides two replicas, resource limits, health probes, and session affinity. CSV uploads remain local to a Streamlit session; this is a local demonstration rather than a distributed stateful production service.

## Verification

```text
python -m unittest discover -s frontend -p "test_*.py" -v
```

The original full-system Streamlit dashboard remains at `serving/dashboard/streamlit_app.py`. This frontend does not claim to operate the original multi-agent or streaming infrastructure. Google Fonts is optional; system-font fallbacks work offline.


## Live data implementation

rontend/live.py fetches the last five days of completed five-minute bars using yfinance. BTC-USD is the default; ETH-USD, US stocks, and RELIANCE.NS are selectable. Yahoo data can be delayed; the UI shows the bar timestamp and warns about old bars. Provider failures are displayed explicitly with no fabricated fallback. The feed is polling, not exchange tick streaming.

The first 80% of feature observations train a StandardScaler + IsolationForest pipeline; the later 20% are scored without fitting on them. Metrics at port 9109 /metrics describe real provider requests and model execution in the Streamlit process. Native execution binds metrics to localhost. Compose exposes them only inside its network, and Prometheus scrapes streamlit:9109. Live values appear after a browser opens Live implementation. Grafana includes live fit duration, holdout anomalies, bar age, and fetch errors. Metrics summarize the latest run across sessions and reset on restart.
