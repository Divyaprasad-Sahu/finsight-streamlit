"""Prepare imports for this project's existing local monitoring resources."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
resources = {
    'docker_network.monitoring': ['docker', 'network', 'inspect', 'frontend_default', '--format', '{{.Id}}'],
    'docker_container.prometheus': ['docker', 'inspect', 'finsight-prometheus', '--format', '{{.Id}}'],
    'docker_container.grafana': ['docker', 'inspect', 'finsight-grafana', '--format', '{{.Id}}'],
}
ids = {name: subprocess.check_output(command, text=True).strip() for name, command in resources.items()}
ids.update({'docker_volume.grafana': 'frontend_grafana-local',
            'docker_volume.prometheus': 'frontend_prometheus-local'})
if not all(ids.values()):
    raise RuntimeError('Missing Docker resource identifiers')
(root / 'local-imports.tf').write_text('\n'.join(
    f'import {{\n  to = {name}\n  id = "{value}"\n}}\n' for name, value in ids.items()))
print('Prepared imports for five existing monitoring resources.')
