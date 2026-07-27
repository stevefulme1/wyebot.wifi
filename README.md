# Wyebot WiFi Collection for Ansible

[![GPL-3.0 License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)

Ansible collection for the **Wyebot WiFi monitoring platform**. Provides
modules for querying sensors, alerts, clients, and network health; EDA event
sources for real-time alert-driven automation; and roles for closed-loop WiFi
remediation that integrate with vendor collections (Aruba, Cisco, Juniper).

> **Note**: This collection is built against the Wyebot REST API. Only the
> `get_locations`, `get_sensors`, `get_sensor_info`, and
> `get_last_network_test_results` endpoints have been confirmed via public
> documentation. Additional modules (alerts, clients, spectrum, etc.) target
> plausible but unconfirmed API endpoints. The API URL, endpoint paths, and
> response field names may need adjustment once validated against a live Wyebot
> environment. Contributions and corrections are welcome.

## Requirements

- Ansible >= 2.16.0
- Python >= 3.12
- A Wyebot Cloud API key ([cloud.wyebot.com](https://cloud.wyebot.com))

Optional (for EDA event sources):

- `aiohttp` >= 3.9.4 (polling and webhook sources)
- `confluent-kafka` >= 2.3.0 (Kafka event source)
- `prometheus-client` >= 0.20.0 (Prometheus metrics scraping)

## Installation

```bash
ansible-galaxy collection install wyebot.wifi
```

Or add to `requirements.yml`:

```yaml
collections:
  - name: wyebot.wifi
```

Install from source:

```bash
ansible-galaxy collection install git+https://github.com/stevefulmer/wyebot.wifi.git
```

## Authentication

All modules require a Wyebot API key. You can provide it per-task or set it
once in a variable file:

```yaml
# group_vars/all.yml
wyebot_api_key: "your-api-key-here"
wyebot_api_url: "https://cloud.wyebot.com/api/v1"  # optional, this is the default
```

## Quick Start

### Query locations and sensors

```yaml
- name: Get all Wyebot locations
  wyebot.wifi.wyebot_locations:
    api_key: "{{ wyebot_api_key }}"
  register: locations

- name: Get sensors at a location
  wyebot.wifi.wyebot_sensors:
    api_key: "{{ wyebot_api_key }}"
    location_id: "{{ locations.locations[0].id }}"
  register: sensors
```

### Check for alerts

```yaml
- name: Get active alerts
  wyebot.wifi.wyebot_alerts:
    api_key: "{{ wyebot_api_key }}"
    location_id: "{{ location_id }}"
  register: alerts

- name: Report critical alerts
  ansible.builtin.debug:
    msg: "Alert: {{ item.message }}"
  loop: "{{ alerts.alerts | selectattr('severity', 'equalto', 'critical') }}"
```

### Detect rogue access points

```yaml
- name: Scan for rogue APs
  wyebot.wifi.wyebot_rogue_aps:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: "{{ sensor_id }}"
  register: rogues

- name: Alert on rogues
  ansible.builtin.debug:
    msg: "Rogue AP detected: {{ item.bssid }} on channel {{ item.channel }}"
  loop: "{{ rogues.rogue_aps }}"
```

### EDA: Alert-driven automation

```yaml
# rulebook.yml
---
- name: Wyebot alert remediation
  hosts: all
  sources:
    - wyebot.wifi.wyebot_alerts:
        api_key: "{{ wyebot_api_key }}"
        poll_interval: 30
  rules:
    - name: Channel congestion detected
      condition: event.alert_type == "channel_congestion"
      action:
        run_playbook:
          name: remediate_channel.yml

    - name: Rogue AP detected
      condition: event.alert_type == "rogue_ap"
      action:
        run_playbook:
          name: remediate_rogue.yml
```

### Closed-loop remediation with vendor collections

The collection is designed to pair with vendor networking collections for
end-to-end remediation:

```yaml
# remediate_channel.yml
- name: Remediate WiFi channel congestion
  hosts: controllers
  tasks:
    - name: Get channel data from Wyebot
      wyebot.wifi.wyebot_channels:
        api_key: "{{ wyebot_api_key }}"
        sensor_id: "{{ sensor_id }}"
      register: channels

    - name: Update AP channel via Aruba controller
      arubanetworks.aoscx.aoscx_config:
        lines:
          - "channel {{ recommended_channel }}"
        parents:
          - "interface radio {{ radio_id }}"
      when: vendor == "aruba"
```

## Included Content

### Modules

| Module | Description |
|--------|-------------|
| `wyebot_locations` | Query Wyebot locations |
| `wyebot_sensors` | Query sensors at a location |
| `wyebot_sensor_info` | Get detailed sensor information |
| `wyebot_network_tests` | Retrieve network test results |
| `wyebot_alerts` | Query alerts by location or sensor |
| `wyebot_clients` | List connected WiFi clients |
| `wyebot_aps` | List access points visible to a sensor |
| `wyebot_ssids` | List SSIDs detected by a sensor |
| `wyebot_channels` | Get channel utilization data |
| `wyebot_interference` | Get RF interference data |
| `wyebot_rogue_aps` | Detect rogue access points |
| `wyebot_spectrum` | Get spectrum analysis data |
| `wyebot_health` | Get sensor health metrics |
| `wyebot_firmware` | Get sensor firmware information |
| `wyebot_api_key` | Create or revoke API keys |

### EDA Event Sources

| Plugin | Description |
|--------|-------------|
| `wyebot_alerts` | Poll Wyebot API for new alerts |
| `wyebot_webhook` | Receive Wyebot webhook callbacks |
| `wyebot_kafka` | Consume Wyebot events from Kafka |

### Roles

| Role | Description |
|------|-------------|
| `remediate_channel` | Closed-loop channel remediation via vendor collections |
| `remediate_rogue` | Rogue AP containment workflow |

## Vendor Integration

This collection focuses on **monitoring and detection**. For remediation, it
integrates with vendor-specific collections:

- **Aruba**: `arubanetworks.aoscx` / `arubanetworks.aruba`
- **Cisco**: `cisco.ios` / `cisco.meraki`
- **Juniper**: `junipernetworks.junos`

## Release Notes

See [CHANGELOG.rst](CHANGELOG.rst).

## Contributing

See [CONTRIBUTING](CONTRIBUTING).

## License

GNU General Public License v3.0 or later.

See [LICENSE](LICENSE) for the full text.
