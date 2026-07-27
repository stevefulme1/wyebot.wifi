# wyebot.wifi.wifi_remediation

Closed-loop WiFi remediation role that gathers alert data from Wyebot sensors and executes vendor-specific remediation actions.

## Requirements

- Ansible >= 2.15
- `wyebot.wifi` collection installed
- Valid Wyebot Cloud API key

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `wyebot_api_key` | `""` | **Required.** Wyebot Cloud API key for authentication. |
| `wyebot_api_url` | `https://cloud.wyebot.com/api/v1` | Wyebot Cloud API base URL. |
| `remediation_vendor` | `aruba` | Vendor platform (`aruba`, `cisco`, `juniper`). |
| `remediation_actions` | `[channel_change, ap_restart]` | List of remediation actions to execute. |
| `notification_webhook` | `""` | Webhook URL for POST notifications. |
| `dry_run` | `true` | Log planned actions without executing them. |

## Vendor Support Matrix

| Action | Aruba | Cisco | Juniper |
|---|---|---|---|
| Channel change | Yes | Yes | Yes |
| AP restart | Yes | Yes | Yes |
| Power adjustment | Yes | Yes | Yes |

Vendor task files are placeholders using `ansible.builtin.debug`. Replace with actual vendor modules (e.g., `cisco.ios`, `juniper.device`) when available.

## Example Playbook

```yaml
- name: Remediate WiFi issues from Wyebot alerts
  hosts: localhost
  roles:
    - role: wyebot.wifi.wifi_remediation
      wyebot_api_key: "{{ vault_wyebot_api_key }}"
      remediation_vendor: aruba
      remediation_actions:
        - channel_change
        - ap_restart
        - power_adjustment
      notification_webhook: "https://hooks.slack.com/services/T00/B00/XXX"
      dry_run: false
```

## License

GPL-3.0-or-later

## Author

Steve Fulmer
