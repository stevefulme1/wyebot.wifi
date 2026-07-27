# wyebot.wifi.prometheus_exporter

Deploy a Wyebot Prometheus exporter container for WiFi metrics collection.

## Requirements

- Docker installed and running on the target host
- `community.docker` Ansible collection installed
- A valid Wyebot Cloud API key

## Role Variables

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `wyebot_prometheus_image` | `wyebotexporter/prometheus:latest` | Container image for the exporter |
| `wyebot_prometheus_port` | `8014` | Host port for the metrics endpoint |
| `wyebot_prometheus_api_key` | `""` **(required)** | Wyebot Cloud API key |
| `wyebot_prometheus_api_url` | `https://cloud.wyebot.com/api/v1` | Wyebot Cloud API base URL |
| `wyebot_prometheus_container_name` | `wyebot-prometheus-exporter` | Docker container name |
| `wyebot_prometheus_restart_policy` | `always` | Container restart policy |

## Dependencies

- `community.docker`

## Example Playbook

```yaml
---
- name: Deploy Wyebot Prometheus exporter
  hosts: monitoring
  roles:
    - role: wyebot.wifi.prometheus_exporter
      wyebot_prometheus_api_key: "{{ vault_wyebot_api_key }}"
```

## License

GPL-3.0-or-later

## Author

Steve Fulmer
