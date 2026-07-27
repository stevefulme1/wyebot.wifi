# wyebot.wifi.sensor_monitor

Continuous sensor health monitoring for the Wyebot WiFi platform.

## Description

This role monitors Wyebot sensor health by querying the Cloud API for sensor and location data. It identifies sensors that are offline or degraded, logs results to disk, generates formatted health reports, and optionally sends email alerts when sensors fall below the configured health threshold.

## Requirements

- Ansible >= 2.15
- `wyebot.wifi` collection (provides `wyebot_sensor_info` and `wyebot_location_info` modules)
- `community.general` collection (provides `community.general.mail` module for email alerts)
- A valid Wyebot Cloud API key

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `wyebot_api_key` | `""` | **(Required)** API key for Wyebot Cloud API authentication. |
| `wyebot_api_url` | `https://cloud.wyebot.com/api/v1` | Base URL of the Wyebot Cloud API. |
| `wyebot_monitor_interval` | `300` | Monitoring interval in seconds between health checks. |
| `wyebot_health_threshold` | `70` | Health score threshold (0-100). Sensors below this trigger alerts. |
| `wyebot_alert_email` | `""` | Email address for unhealthy sensor alerts. Empty disables alerts. |
| `wyebot_monitor_log_path` | `/var/log/wyebot` | Directory for health check logs and reports. |

## Example Playbook

```yaml
---
- name: Monitor Wyebot sensor health
  hosts: monitoring
  roles:
    - role: wyebot.wifi.sensor_monitor
      wyebot_api_key: "{{ vault_wyebot_api_key }}"
      wyebot_health_threshold: 80
      wyebot_alert_email: "ops-team@example.com"
      wyebot_monitor_log_path: "/opt/wyebot/logs"
```

### Scheduled monitoring with `ansible.builtin.cron`

```yaml
---
- name: Set up recurring Wyebot health checks
  hosts: monitoring
  tasks:
    - name: Schedule health check every 5 minutes
      ansible.builtin.cron:
        name: "wyebot-health-check"
        minute: "*/5"
        job: >-
          ansible-playbook /opt/playbooks/wyebot_health_check.yml
          -e wyebot_api_key={{ vault_wyebot_api_key }}
```

## Platforms

- EL 8, 9
- Ubuntu 20.04 (Focal), 22.04 (Jammy)

## License

GPL-3.0-or-later

## Author

Steve Fulmer
