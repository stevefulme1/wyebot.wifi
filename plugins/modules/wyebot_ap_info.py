#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_ap_info
author: Steve Fulmer (@stevefulmer)
version_added: "1.0.0"
short_description: Retrieve access point inventory and health from Wyebot.
description:
  - Get information about access points detected by a Wyebot sensor.
  - Includes AP health metrics such as client count, utilization, and signal strength.
  - Results can be filtered by I(bssid) or I(band).
options:
  api_key:
    description: API key for authenticating with the Wyebot Cloud API.
    type: str
    required: true
    no_log: true
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
  sensor_id:
    description: The ID of the sensor to retrieve access point data from.
    type: int
    required: true
  bssid:
    description: Filter results to a specific access point by BSSID.
    type: str
  band:
    description: Filter results by radio band.
    type: str
    choices:
      - "2.4GHz"
      - "5GHz"
      - "6GHz"
"""

EXAMPLES = r"""
- name: Get all access points seen by a sensor
  wyebot.wifi.wyebot_ap_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: all_aps

- name: Get 5GHz access points only
  wyebot.wifi.wyebot_ap_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    band: "5GHz"
  register: aps_5ghz

- name: Get a specific access point
  wyebot.wifi.wyebot_ap_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    bssid: "AA:BB:CC:DD:EE:01"
  register: ap

- name: Show overloaded APs
  ansible.builtin.debug:
    msg: >-
      AP {{ item.bssid }} ({{ item.ssid }}) has {{ item.clients_count }} clients
      and {{ item.utilization_pct }}% utilization
  loop: "{{ all_aps.access_points }}"
  when: item.utilization_pct > 80
"""

RETURN = r"""
access_points:
  description: List of access points detected by the sensor.
  type: list
  elements: dict
  returned: always
  contains:
    bssid:
      description: BSSID (MAC address) of the access point.
      type: str
      returned: always
      sample: "AA:BB:CC:DD:EE:01"
    ssid:
      description: SSID broadcast by the access point.
      type: str
      returned: always
      sample: "Corporate-WiFi"
    band:
      description: Radio band the access point operates on.
      type: str
      returned: always
      sample: "5GHz"
    channel:
      description: Wireless channel number.
      type: int
      returned: always
      sample: 36
    channel_width:
      description: Channel width in MHz.
      type: int
      returned: always
      sample: 80
    signal_strength:
      description: Signal strength in dBm as seen by the sensor.
      type: int
      returned: always
      sample: -45
    clients_count:
      description: Number of clients currently associated with this AP.
      type: int
      returned: always
      sample: 12
    utilization_pct:
      description: Channel utilization percentage.
      type: float
      returned: always
      sample: 35.5
    vendor:
      description: Vendor or manufacturer of the access point.
      type: str
      returned: always
      sample: "Cisco"
  sample:
    - bssid: "AA:BB:CC:DD:EE:01"
      ssid: "Corporate-WiFi"
      band: "5GHz"
      channel: 36
      channel_width: 80
      signal_strength: -45
      clients_count: 12
      utilization_pct: 35.5
      vendor: "Cisco"
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
        sensor_id=dict(type='int', required=True),
        bssid=dict(type='str'),
        band=dict(type='str', choices=['2.4GHz', '5GHz', '6GHz']),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)

    try:
        result = client.get_aps(module.params['sensor_id'])
    except WyebotAPIError as exc:
        module.fail_json(msg=str(exc))
        return

    aps = result if isinstance(result, list) else result.get('access_points', [result])

    # Client-side BSSID filtering
    bssid = module.params.get('bssid')
    if bssid is not None:
        bssid_upper = bssid.upper()
        aps = [ap for ap in aps if ap.get('bssid', '').upper() == bssid_upper]

    # Client-side band filtering
    band = module.params.get('band')
    if band is not None:
        aps = [ap for ap in aps if ap.get('band') == band]

    module.exit_json(changed=False, access_points=aps)


if __name__ == '__main__':
    main()
