# Local monitoring with Terraform

This module manages the running Grafana and Prometheus containers, network, and two persistent Docker volumes. No AWS or Azure resources are created.

## Bootstrap and adopt

From the repository root, start Docker Desktop and the local Streamlit application in another terminal. Open the Live implementation view so port 9109 publishes actual model metrics.

```powershell
python frontend/setup_monitoring.py
docker compose -f frontend/monitoring-local.yml up -d
python frontend/terraform/monitoring/adopt_local.py
terraform -chdir=frontend/terraform/monitoring init
$env:TF_VAR_grafana_password = ((Get-Content frontend/.env | Where-Object { $_.StartsWith('GRAFANA_ADMIN_PASSWORD=') }) -split '=',2)[1]
terraform -chdir=frontend/terraform/monitoring plan
terraform -chdir=frontend/terraform/monitoring apply
```

Terraform 1.13.5 was installed locally under `.tools/terraform/terraform.exe` on the development machine. Use that executable if Terraform is not on PATH. The module uses Docker provider 4.6.0. On Linux/macOS override `docker_host` with the daemon endpoint for your platform.

The initial adoption imports existing resources and replaces the two containers while retaining the volumes. Once Terraform owns them, use Terraform for updates rather than Compose down/up. The checked setup applied successfully and a subsequent plan reported no changes.

Open [Grafana](http://localhost:3000/d/finsight-live/finsight-live-ml-monitoring) and [Prometheus](http://localhost:9090/targets). Grafana allows a Viewer on localhost; the generated admin password stays in ignored `frontend/.env`. State and plans contain sensitive values and must stay out of Git.

Grafana monitors the local Streamlit process, not the public Community Cloud app. Keep the local Live implementation view open for periodic fits. Sparse initial plots fill as Prometheus collects five-second samples. Cached `latest` image tags were used to avoid downloads; pin verified digests for reproducible production use.
