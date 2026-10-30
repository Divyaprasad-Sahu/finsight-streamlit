terraform {
  required_version = ">= 1.5"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 4.6"
    }
  }
}

variable "docker_host" {
  description = "Docker Desktop on Windows; override for Linux/macOS."
  type        = string
  default     = "npipe:////./pipe/docker_engine"
}

variable "grafana_password" {
  type      = string
  sensitive = true
}

provider "docker" {
  host = var.docker_host
}

# Use images already cached locally, avoiding a download on each apply.
data "docker_image" "grafana" {
  name = "grafana/grafana:latest"
}
data "docker_image" "prometheus" {
  name = "prom/prometheus:latest"
}

resource "docker_network" "monitoring" {
  name = "frontend_default"
  lifecycle { ignore_changes = [labels] }
}

resource "docker_volume" "grafana" {
  name = "frontend_grafana-local"
  lifecycle { ignore_changes = [labels] }
}
resource "docker_volume" "prometheus" {
  name = "frontend_prometheus-local"
  lifecycle { ignore_changes = [labels] }
}

locals {
  monitoring_dir = abspath("${path.module}/../../monitoring")
}

resource "docker_container" "prometheus" {
  name    = "finsight-prometheus"
  image   = data.docker_image.prometheus.id
  restart = "unless-stopped"
  ports {
    internal = 9090
    external = 9090
    ip       = "127.0.0.1"
  }
  networks_advanced {
    name    = docker_network.monitoring.name
    aliases = ["prometheus"]
  }
  volumes {
    host_path      = "${local.monitoring_dir}/prometheus-local.yml"
    container_path = "/etc/prometheus/prometheus.yml"
    read_only      = true
  }
  volumes {
    volume_name    = docker_volume.prometheus.name
    container_path = "/prometheus"
  }
}

resource "docker_container" "grafana" {
  name    = "finsight-grafana"
  image   = data.docker_image.grafana.id
  restart = "unless-stopped"
  env = [
    "GF_AUTH_ANONYMOUS_ENABLED=true",
    "GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer",
    "GF_SECURITY_ADMIN_PASSWORD=${var.grafana_password}",
    "GF_USERS_ALLOW_SIGN_UP=false",
  ]
  ports {
    internal = 3000
    external = 3000
    ip       = "127.0.0.1"
  }
  networks_advanced {
    name    = docker_network.monitoring.name
    aliases = ["grafana"]
  }
  volumes {
    host_path      = "${local.monitoring_dir}/grafana/provisioning"
    container_path = "/etc/grafana/provisioning"
    read_only      = true
  }
  volumes {
    host_path      = "${local.monitoring_dir}/grafana/live-dashboard.json"
    container_path = "/var/lib/grafana/dashboards/finsight-live.json"
    read_only      = true
  }
  volumes {
    volume_name    = docker_volume.grafana.name
    container_path = "/var/lib/grafana"
  }
  depends_on = [docker_container.prometheus]
}

output "grafana_dashboard" {
  value = "http://localhost:3000/d/finsight-live/finsight-live-ml-monitoring"
}
output "prometheus" {
  value = "http://localhost:9090"
}
