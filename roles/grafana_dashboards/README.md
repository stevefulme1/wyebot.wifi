# wyebot.wifi.grafana_dashboards

Install Wyebot Grafana dashboard templates for WiFi sensor monitoring.

## Description

This role creates a Grafana folder and uploads pre-built dashboard JSON
templates via the Grafana HTTP API. Dashboards provide visibility into Wyebot
sensor health, network performance, alerts, and RF spectrum data using
Prometheus-backed `wyebot_*` metrics.

## Requirements

- Grafana instance accessible from the controller
- Grafana API key or service account token with folder and dashboard write
  permissions
- Prometheus data source configured in Grafana with Wyebot metric endpoints

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `grafana_url` | `http://localhost:3000` | Base URL of the Grafana instance |
| `grafana_api_key` | `""` | Grafana API key (required, `no_log`) |
| `wyebot_dashboard_folder` | `Wyebot` | Grafana folder name for dashboards |
| `wyebot_dashboards` | `[sensor_overview, network_health, alerts, spectrum]` | Dashboard templates to upload |

## Included Dashboards

| Template | Panels |
|---|---|
| `sensor_overview` | Sensor online/offline status, health score gauge, network test results table, uptime graph |
| `network_health` | Overall health gauge, channel utilization heatmap, signal strength distribution, test pass/fail rates, client count time series |
| `alerts` | Placeholder for alert-specific panels |
| `spectrum` | Placeholder for RF spectrum analysis panels |

## Example Playbook

```yaml
- name: Deploy Wyebot Grafana dashboards
  hosts: grafana_servers
  roles:
    - role: wyebot.wifi.grafana_dashboards
      grafana_url: "https://grafana.example.com"
      grafana_api_key: "{{ vault_grafana_api_key }}"
      wyebot_dashboard_folder: "Wyebot Production"
```

## License

GPL-3.0-or-later

## Author

Steve Fulmer
