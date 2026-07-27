#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_interference_info
short_description: Get RF interference detection data from Wyebot sensors
version_added: "1.0.0"
description:
  - Retrieve RF interference detection data from Wyebot wireless sensors.
  - Returns interference events including type, source, frequency,
    severity, and duration.
  - Results can be filtered client-side by interference type.
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
    description: ID of the sensor to retrieve interference data from.
    type: int
    required: true
  interference_type:
    description:
      - Filter by interference type.
      - Filtering is applied client-side after retrieving all interference data.
    type: str
    choices:
      - co_channel
      - adjacent_channel
      - non_wifi
"""

EXAMPLES = r"""
- name: Get all interference data for a sensor
  wyebot.wifi.wyebot_interference_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: interference_data

- name: Get only non-WiFi interference
  wyebot.wifi.wyebot_interference_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    interference_type: non_wifi
  register: non_wifi_interference

- name: Display high severity interference events
  ansible.builtin.debug:
    msg: "Interference: {{ item.type }} on channel {{ item.channel_affected }} - {{ item.severity }}"
  loop: "{{ interference_data.interference }}"
  when: item.severity == "high"
"""

RETURN = r"""
interference:
  description: List of interference detection events.
  type: list
  elements: dict
  returned: always
  sample:
    - type: "co_channel"
      source: "neighboring_ap"
      frequency_mhz: 2437
      severity: "high"
      channel_affected: 6
      timestamp: "2024-01-15T10:30:00Z"
      duration_seconds: 300
  contains:
    type:
      description: Type of interference detected.
      type: str
      returned: always
    source:
      description: Identified source of the interference.
      type: str
      returned: always
    frequency_mhz:
      description: Frequency in MHz where interference was detected.
      type: int
      returned: always
    severity:
      description: Severity level of the interference.
      type: str
      returned: always
    channel_affected:
      description: Channel number affected by the interference.
      type: int
      returned: always
    timestamp:
      description: Timestamp when the interference was detected.
      type: str
      returned: always
    duration_seconds:
      description: Duration of the interference event in seconds.
      type: int
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
        sensor_id=dict(type="int", required=True),
        interference_type=dict(
            type="str",
            choices=["co_channel", "adjacent_channel", "non_wifi"],
        ),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)

    try:
        result = client.get_interference(module.params["sensor_id"])
    except WyebotAPIError as e:
        module.fail_json(
            msg="Failed to retrieve interference data: {0}".format(str(e)),
            status_code=e.status_code,
        )
        return

    interference = result.get("interference", result) if isinstance(result, dict) else result
    if not isinstance(interference, list):
        interference = [interference] if interference else []

    itype = module.params.get("interference_type")
    if itype:
        interference = [i for i in interference if i.get("type") == itype]

    module.exit_json(changed=False, interference=interference)


if __name__ == "__main__":
    main()
