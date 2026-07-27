#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_ssid_info
author: Steve Fulmer (@stevefulmer)
version_added: "1.0.0"
short_description: Retrieve SSID information from Wyebot.
description:
  - Get information about SSIDs detected by a Wyebot sensor.
  - Includes security type, associated BSSIDs, client count, and signal metrics.
  - Results can be filtered to a specific SSID using I(ssid_name).
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
    description: The ID of the sensor to retrieve SSID data from.
    type: int
    required: true
  ssid_name:
    description: Filter results to a specific SSID by name.
    type: str
"""

EXAMPLES = r"""
- name: Get all SSIDs seen by a sensor
  wyebot.wifi.wyebot_ssid_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: all_ssids

- name: Get a specific SSID
  wyebot.wifi.wyebot_ssid_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    ssid_name: "Corporate-WiFi"
  register: corp_ssid

- name: Show SSIDs with open security
  ansible.builtin.debug:
    msg: "WARNING: {{ item.name }} has {{ item.security_type }} security"
  loop: "{{ all_ssids.ssids }}"
  when: item.security_type == 'open'
"""

RETURN = r"""
ssids:
  description: List of SSIDs detected by the sensor.
  type: list
  elements: dict
  returned: always
  contains:
    name:
      description: Name of the SSID.
      type: str
      returned: always
      sample: "Corporate-WiFi"
    bssid_list:
      description: List of BSSIDs broadcasting this SSID.
      type: list
      elements: str
      returned: always
      sample:
        - "AA:BB:CC:DD:EE:01"
        - "AA:BB:CC:DD:EE:02"
    security_type:
      description: Security protocol used by the SSID.
      type: str
      returned: always
      sample: "WPA3-Enterprise"
    band:
      description: Radio band or bands the SSID is available on.
      type: str
      returned: always
      sample: "5GHz"
    client_count:
      description: Number of clients currently connected to this SSID.
      type: int
      returned: always
      sample: 45
    avg_signal_strength:
      description: Average signal strength in dBm across all clients on this SSID.
      type: float
      returned: always
      sample: -58.3
  sample:
    - name: "Corporate-WiFi"
      bssid_list:
        - "AA:BB:CC:DD:EE:01"
        - "AA:BB:CC:DD:EE:02"
      security_type: "WPA3-Enterprise"
      band: "5GHz"
      client_count: 45
      avg_signal_strength: -58.3
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
        ssid_name=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)

    try:
        result = client.get_ssids(module.params['sensor_id'])
    except WyebotAPIError as exc:
        module.fail_json(msg=str(exc))
        return

    ssids = result if isinstance(result, list) else result.get('ssids', [result])

    # Client-side SSID name filtering
    ssid_name = module.params.get('ssid_name')
    if ssid_name is not None:
        ssids = [s for s in ssids if s.get('name') == ssid_name]

    module.exit_json(changed=False, ssids=ssids)


if __name__ == '__main__':
    main()
