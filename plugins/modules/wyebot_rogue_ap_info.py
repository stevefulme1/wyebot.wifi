#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_rogue_ap_info
short_description: Get rogue AP detection data from Wyebot sensors
version_added: "1.0.0"
description:
  - Retrieve rogue access point detection data from Wyebot wireless sensors.
  - Returns detected APs classified as rogue, neighbor, or authorized
    along with signal strength, channel, and vendor information.
  - Results can be filtered client-side by classification and acknowledged state.
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
    description: ID of the sensor to retrieve rogue AP data from.
    type: int
    required: true
  classification:
    description:
      - Filter by AP classification.
      - Filtering is applied client-side after retrieving all rogue AP data.
    type: str
    choices:
      - rogue
      - neighbor
      - authorized
  acknowledged:
    description:
      - Filter by acknowledged state.
      - Filtering is applied client-side after retrieving all rogue AP data.
    type: bool
"""

EXAMPLES = r"""
- name: Get all rogue AP data for a sensor
  wyebot.wifi.wyebot_rogue_ap_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: rogue_data

- name: Get only unacknowledged rogue APs
  wyebot.wifi.wyebot_rogue_ap_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    classification: rogue
    acknowledged: false
  register: unacked_rogues

- name: Report rogue APs
  ansible.builtin.debug:
    msg: "Rogue AP {{ item.bssid }} ({{ item.ssid }}) on channel {{ item.channel }}"
  loop: "{{ rogue_data.rogue_aps }}"
  when: item.classification == "rogue"
"""

RETURN = r"""
rogue_aps:
  description: List of detected rogue access points.
  type: list
  elements: dict
  returned: always
  sample:
    - bssid: "AA:BB:CC:DD:EE:FF"
      ssid: "EvilTwin"
      classification: "rogue"
      signal_strength: -65
      channel: 6
      band: "2.4GHz"
      first_seen: "2024-01-10T08:00:00Z"
      last_seen: "2024-01-15T10:30:00Z"
      vendor: "Unknown"
      acknowledged: false
  contains:
    bssid:
      description: BSSID (MAC address) of the detected AP.
      type: str
      returned: always
    ssid:
      description: SSID broadcast by the detected AP.
      type: str
      returned: always
    classification:
      description: Classification of the detected AP.
      type: str
      returned: always
    signal_strength:
      description: Signal strength in dBm.
      type: int
      returned: always
    channel:
      description: Channel the AP is operating on.
      type: int
      returned: always
    band:
      description: Wireless band of the detected AP.
      type: str
      returned: always
    first_seen:
      description: Timestamp when the AP was first detected.
      type: str
      returned: always
    last_seen:
      description: Timestamp when the AP was last seen.
      type: str
      returned: always
    vendor:
      description: Vendor identification from OUI lookup.
      type: str
      returned: always
    acknowledged:
      description: Whether the AP has been acknowledged by an administrator.
      type: bool
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
        classification=dict(
            type="str",
            choices=["rogue", "neighbor", "authorized"],
        ),
        acknowledged=dict(type="bool"),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)

    try:
        result = client.get_rogue_aps(module.params["sensor_id"])
    except WyebotAPIError as e:
        module.fail_json(
            msg="Failed to retrieve rogue AP data: {0}".format(str(e)),
            status_code=e.status_code,
        )
        return

    rogue_aps = result.get("rogue_aps", result) if isinstance(result, dict) else result
    if not isinstance(rogue_aps, list):
        rogue_aps = [rogue_aps] if rogue_aps else []

    classification = module.params.get("classification")
    if classification:
        rogue_aps = [ap for ap in rogue_aps if ap.get("classification") == classification]

    acknowledged = module.params.get("acknowledged")
    if acknowledged is not None:
        rogue_aps = [ap for ap in rogue_aps if ap.get("acknowledged") == acknowledged]

    module.exit_json(changed=False, rogue_aps=rogue_aps)


if __name__ == "__main__":
    main()
