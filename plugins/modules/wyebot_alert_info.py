#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_alert_info
author: Steve Fulmer (@stevefulmer)
version_added: "1.0.0"
short_description: Retrieve active Wyebot alerts.
description:
  - Get active alerts from the Wyebot platform.
  - Alerts can be filtered by I(location_id), I(sensor_id), and I(severity).
  - Returns alerts sorted by most recent first.
options:
  api_key:
    description: API key for authenticating with the Wyebot Cloud API.
    type: str
    required: true
  api_url:
    description: Base URL of the Wyebot Cloud API.
    type: str
    default: https://cloud.wyebot.com/api/v1
  validate_certs:
    description: Whether to validate SSL certificates when connecting to the API.
    type: bool
    default: true
  timeout:
    description: Timeout in seconds for API requests.
    type: int
    default: 30
  location_id:
    description: Filter alerts by location ID.
    type: int
  sensor_id:
    description: Filter alerts by sensor ID.
    type: int
  severity:
    description: Filter alerts by severity level.
    type: str
    choices:
      - critical
      - warning
      - info
  limit:
    description: Maximum number of alerts to return.
    type: int
    default: 50
"""

EXAMPLES = r"""
- name: Get all active alerts
  wyebot.wifi.wyebot_alert_info:
    api_key: "{{ wyebot_api_key }}"
  register: all_alerts

- name: Get critical alerts for a location
  wyebot.wifi.wyebot_alert_info:
    api_key: "{{ wyebot_api_key }}"
    location_id: 42
    severity: critical
  register: critical_alerts

- name: Get alerts for a specific sensor
  wyebot.wifi.wyebot_alert_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    limit: 10
  register: sensor_alerts

- name: Count unacknowledged critical alerts
  ansible.builtin.debug:
    msg: >-
      {{ all_alerts.alerts
         | selectattr('severity', 'equalto', 'critical')
         | rejectattr('acknowledged')
         | list | length }} unacknowledged critical alerts
"""

RETURN = r"""
alerts:
  description: List of active alerts.
  type: list
  elements: dict
  returned: always
  contains:
    id:
      description: Unique identifier for the alert.
      type: int
      returned: always
      sample: 5001
    severity:
      description: Severity level of the alert.
      type: str
      returned: always
      sample: "critical"
    category:
      description: Category or type of the alert.
      type: str
      returned: always
      sample: "connectivity"
    message:
      description: Human-readable alert message.
      type: str
      returned: always
      sample: "DHCP response time exceeds 5 seconds"
    sensor_id:
      description: ID of the sensor that generated the alert.
      type: int
      returned: always
      sample: 101
    location_id:
      description: ID of the location associated with the alert.
      type: int
      returned: always
      sample: 42
    timestamp:
      description: ISO 8601 timestamp of when the alert was created.
      type: str
      returned: always
      sample: "2025-01-15T10:30:00Z"
    acknowledged:
      description: Whether the alert has been acknowledged by an operator.
      type: bool
      returned: always
      sample: false
  sample:
    - id: 5001
      severity: "critical"
      category: "connectivity"
      message: "DHCP response time exceeds 5 seconds"
      sensor_id: 101
      location_id: 42
      timestamp: "2025-01-15T10:30:00Z"
      acknowledged: false
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wyebot.wifi.plugins.module_utils.wyebot_api import (
    WyebotAPI,
    WyebotAPIError,
    wyebot_argument_spec,
)


def main():
    """Entry point for module execution."""
    argument_spec = wyebot_argument_spec()
    argument_spec.update(dict(
        location_id=dict(type='int'),
        sensor_id=dict(type='int'),
        severity=dict(type='str', choices=['critical', 'warning', 'info']),
        limit=dict(type='int', default=50),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)

    try:
        result = client.get_alerts(
            location_id=module.params.get('location_id'),
            sensor_id=module.params.get('sensor_id'),
        )
    except WyebotAPIError as exc:
        module.fail_json(msg=str(exc))
        return

    alerts = result if isinstance(result, list) else result.get('alerts', [result])

    # Client-side severity filtering
    severity = module.params.get('severity')
    if severity is not None:
        alerts = [a for a in alerts if a.get('severity') == severity]

    # Client-side limit
    limit = module.params['limit']
    alerts = alerts[:limit]

    module.exit_json(changed=False, alerts=alerts)


if __name__ == '__main__':
    main()
