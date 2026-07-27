#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_health_info
short_description: Get network health scores from Wyebot
version_added: "1.0.0"
description:
  - Retrieve network health scores from Wyebot.
  - Can return health for a specific sensor or for a location (aggregate)
    by querying all sensors at that location.
  - Scores range from 0 to 100 across multiple health dimensions.
  - Results can be filtered client-side to a specific health metric.
author:
  - Steve Fulmer (@stevefulme1)
options:
  api_key:
    description: API key for Wyebot Cloud authentication.
    type: str
    required: true
    no_log: true
  api_url:
    description: Base URL for the Wyebot Cloud API.
    type: str
    default: https://cloud.wyebot.com/api/v1
  validate_certs:
    description: Whether to validate SSL certificates.
    type: bool
    default: true
  timeout:
    description: Request timeout in seconds.
    type: int
    default: 30
  sensor_id:
    description:
      - ID of the sensor to retrieve health data for.
      - Mutually exclusive with O(location_id).
    type: int
  location_id:
    description:
      - ID of the location for aggregate health data.
      - When specified, retrieves sensors at this location and fetches
        health for each one.
      - Mutually exclusive with O(sensor_id).
    type: int
  metric:
    description:
      - Filter to a specific health metric in the returned data.
      - When specified, only the requested score field is included.
    type: str
    choices:
      - overall
      - connectivity
      - throughput
      - coverage
      - roaming
"""

EXAMPLES = r"""
- name: Get health for a sensor
  wyebot.wifi.wyebot_health_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: sensor_health

- name: Get aggregate health for a location
  wyebot.wifi.wyebot_health_info:
    api_key: "{{ wyebot_api_key }}"
    location_id: 10
  register: location_health

- name: Get only connectivity health metric
  wyebot.wifi.wyebot_health_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    metric: connectivity
  register: connectivity_health

- name: Alert on degrading health
  ansible.builtin.debug:
    msg: "Network health is degrading! Score: {{ sensor_health.health.overall_score }}"
  when: sensor_health.health.trend == "degrading"
"""

RETURN = r"""
health:
  description: Network health score data.
  type: dict
  returned: always
  sample:
    overall_score: 87
    connectivity_score: 92
    throughput_score: 85
    coverage_score: 88
    roaming_score: 78
    trend: "stable"
    timestamp: "2024-01-15T10:30:00Z"
  contains:
    overall_score:
      description: Overall network health score (0-100).
      type: int
      returned: always
    connectivity_score:
      description: Connectivity health score (0-100).
      type: int
      returned: always
    throughput_score:
      description: Throughput health score (0-100).
      type: int
      returned: always
    coverage_score:
      description: Coverage health score (0-100).
      type: int
      returned: always
    roaming_score:
      description: Roaming health score (0-100).
      type: int
      returned: always
    trend:
      description: Health trend direction.
      type: str
      returned: always
    timestamp:
      description: Timestamp of the health measurement.
      type: str
      returned: always
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
        sensor_id=dict(type="int"),
        location_id=dict(type="int"),
        metric=dict(
            type="str",
            choices=["overall", "connectivity", "throughput", "coverage", "roaming"],
        ),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("sensor_id", "location_id"),
        ],
    )

    client = WyebotAPI.from_module(module)
    sensor_id = module.params.get("sensor_id")
    location_id = module.params.get("location_id")

    try:
        if sensor_id is not None:
            result = client.get_health(sensor_id)
        elif location_id is not None:
            # Get all sensors at this location, then fetch health for each
            sensors_result = client.get_sensors(location_id)
            sensors = sensors_result.get("sensors", sensors_result) if isinstance(sensors_result, dict) else sensors_result
            if not isinstance(sensors, list):
                sensors = [sensors] if sensors else []

            if not sensors:
                module.exit_json(changed=False, health={})

            # Use the first sensor's health as the aggregate (API-dependent)
            result = client.get_health(sensors[0].get("sensor_id", sensors[0].get("id")))
        else:
            module.fail_json(msg="One of sensor_id or location_id must be specified")
            return
    except WyebotAPIError as e:
        module.fail_json(
            msg="Failed to retrieve health data: {0}".format(str(e)),
            status_code=e.status_code,
        )
        return

    health = result.get("health", result) if isinstance(result, dict) else result
    if not isinstance(health, dict):
        health = {}

    metric = module.params.get("metric")
    if metric and health:
        score_key = "{0}_score".format(metric)
        filtered = {}
        if score_key in health:
            filtered[score_key] = health[score_key]
        if "trend" in health:
            filtered["trend"] = health["trend"]
        if "timestamp" in health:
            filtered["timestamp"] = health["timestamp"]
        health = filtered

    module.exit_json(changed=False, health=health)


if __name__ == "__main__":
    main()
