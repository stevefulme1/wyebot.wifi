#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_client_info
author: Steve Fulmer (@stevefulmer)
version_added: "1.0.0"
short_description: Retrieve connected client and device data from Wyebot.
description:
  - Get information about wireless clients connected to networks monitored by a Wyebot sensor.
  - Results can be filtered by I(mac_address) for a specific client or by I(ssid).
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
    description: The ID of the sensor to retrieve client data from.
    type: int
    required: true
  mac_address:
    description: Filter results to a specific client by MAC address.
    type: str
  ssid:
    description: Filter results to clients connected to a specific SSID.
    type: str
"""

EXAMPLES = r"""
- name: Get all clients seen by a sensor
  wyebot.wifi.wyebot_client_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: all_clients

- name: Get a specific client by MAC address
  wyebot.wifi.wyebot_client_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    mac_address: "11:22:33:44:55:66"
  register: client

- name: Get clients on a specific SSID
  wyebot.wifi.wyebot_client_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    ssid: "Corporate-WiFi"
  register: corp_clients

- name: Show clients with weak signal
  ansible.builtin.debug:
    msg: "{{ item.hostname }} has weak signal: {{ item.signal_strength }} dBm"
  loop: "{{ all_clients.clients }}"
  when: item.signal_strength < -70
"""

RETURN = r"""
clients:
  description: List of connected wireless clients.
  type: list
  elements: dict
  returned: always
  contains:
    mac_address:
      description: MAC address of the client device.
      type: str
      returned: always
      sample: "11:22:33:44:55:66"
    ip_address:
      description: IP address assigned to the client.
      type: str
      returned: always
      sample: "192.168.1.50"
    hostname:
      description: Hostname of the client device if available.
      type: str
      returned: always
      sample: "janes-laptop"
    ssid:
      description: SSID the client is connected to.
      type: str
      returned: always
      sample: "Corporate-WiFi"
    bssid:
      description: BSSID of the access point the client is associated with.
      type: str
      returned: always
      sample: "AA:BB:CC:DD:EE:01"
    band:
      description: Radio band the client is operating on.
      type: str
      returned: always
      sample: "5GHz"
    channel:
      description: Wireless channel number.
      type: int
      returned: always
      sample: 36
    signal_strength:
      description: Signal strength in dBm.
      type: int
      returned: always
      sample: -55
    snr:
      description: Signal-to-noise ratio in dB.
      type: int
      returned: always
      sample: 35
    tx_rate:
      description: Transmit rate in Mbps.
      type: float
      returned: always
      sample: 866.7
    rx_rate:
      description: Receive rate in Mbps.
      type: float
      returned: always
      sample: 585.0
  sample:
    - mac_address: "11:22:33:44:55:66"
      ip_address: "192.168.1.50"
      hostname: "janes-laptop"
      ssid: "Corporate-WiFi"
      bssid: "AA:BB:CC:DD:EE:01"
      band: "5GHz"
      channel: 36
      signal_strength: -55
      snr: 35
      tx_rate: 866.7
      rx_rate: 585.0
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
        mac_address=dict(type='str'),
        ssid=dict(type='str'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)

    try:
        result = client.get_clients(module.params['sensor_id'])
    except WyebotAPIError as exc:
        module.fail_json(msg=str(exc))
        return

    clients = result if isinstance(result, list) else result.get('clients', [result])

    # Client-side MAC address filtering
    mac_address = module.params.get('mac_address')
    if mac_address is not None:
        mac_upper = mac_address.upper()
        clients = [
            c for c in clients
            if c.get('mac_address', '').upper() == mac_upper
        ]

    # Client-side SSID filtering
    ssid = module.params.get('ssid')
    if ssid is not None:
        clients = [c for c in clients if c.get('ssid') == ssid]

    module.exit_json(changed=False, clients=clients)


if __name__ == '__main__':
    main()
