terraform {
  required_version = ">= 1.5"
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# Uses the local Docker daemon. Docker Desktop must be running.
provider "docker" {}

variable "port" {
  type    = number
  default = 8501
}

resource "docker_image" "streamlit" {
  name = "finsight-streamlit:terraform"
  build {
    context    = abspath("${path.module}/../..")
    dockerfile = "frontend/Dockerfile"
  }
  triggers = {
    source = sha256(join("", [for f in ["app.py", "model.py", "dashboard.html", "requirements.txt", "Dockerfile"] : filesha256("${path.module}/../${f}")]))
  }
}

resource "docker_container" "streamlit" {
  name  = "finsight-streamlit-tf"
  image = docker_image.streamlit.image_id
  ports {
    internal = 8501
    external = var.port
    ip       = "127.0.0.1"
  }
}

output "dashboard_url" {
  value = "http://localhost:${var.port}"
}
