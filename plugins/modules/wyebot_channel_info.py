#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_channel_info
short_description: Get channel utilization metrics from Wyebot sensors
version_added: "1.0.0"
description:
  - Retrieve channel utilization metrics from Wyebot wireless sensors.
  - Returns data including utilization percentage, noise floor, AP count,
    and interference metrics per channel.
  - Results can be filtered client-side by band.
author:
  - Steve Fulmer (@stevefulme1)
options:
  api_key:
    description: API key for Wyebot Cloud authentication.
    type: str
    required: true
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
    description: ID of the sensor to retrieve channel data from.
    type: int
    required: true
  band:
    description:
      - Filter channels by wireless band.
      - Filtering is applied client-side after retrieving all channel data.
    type: str
    choices:
      - 2.4GHz
      - 5GHz
      - 6GHz
"""

EXAMPLES = r"""
- name: Get all channel utilization data for a sensor
  wyebot.wifi.wyebot_channel_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: channel_data

- name: Get 5GHz channel data only
  wyebot.wifi.wyebot_channel_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    band: "5GHz"
  register: channel_5ghz

- name: Display channels with high utilization
  ansible.builtin.debug:
    msg: "Channel {{ item.channel_number }} utilization: {{ item.utilization_pct }}%"
  loop: "{{ channel_data.channels }}"
  when: item.utilization_pct | int > 70
"""

RETURN = r"""
channels:
  description: List of channel utilization metrics.
  type: list
  elements: dict
  returned: always
  sample:
    - channel_number: 6
      band: "2.4GHz"
      utilization_pct: 45.2
      noise_floor_dbm: -95
      ap_count: 3
      interference_pct: 12.5
      co_channel_interference_pct: 8.1
  contains:
    channel_number:
      description: Channel number.
      type: int
      returned: always
    band:
      description: Wireless band for this channel.
      type: str
      returned: always
    utilization_pct:
      description: Channel utilization percentage.
      type: float
      returned: always
    noise_floor_dbm:
      description: Noise floor in dBm.
      type: int
      returned: always
    ap_count:
      description: Number of access points detected on this channel.
      type: int
      returned: always
    interference_pct:
      description: Total interference percentage.
      type: float
      returned: always
    co_channel_interference_pct:
      description: Co-channel interference percentage.
      type: float
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
        band=dict(type="str", choices=["2.4GHz", "5GHz", "6GHz"]),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)

    try:
        result = client.get_channels(module.params["sensor_id"])
    except WyebotAPIError as e:
        module.fail_json(
            msg="Failed to retrieve channel data: {0}".format(str(e)),
            status_code=e.status_code,
        )
        return

    channels = result.get("channels", result) if isinstance(result, dict) else result
    if not isinstance(channels, list):
        channels = [channels] if channels else []

    band = module.params.get("band")
    if band:
        channels = [c for c in channels if c.get("band") == band]

    module.exit_json(changed=False, channels=channels)


if __name__ == "__main__":
    main()
