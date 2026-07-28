#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_sensor_info
author: Steve Fulmer (@stevefulmer)
version_added: "1.0.0"
short_description: Retrieve Wyebot sensor details.
description:
  - Get information about Wyebot sensors.
  - Can retrieve a specific sensor by I(sensor_id) or list all sensors at a I(location_id).
  - When I(sensor_id) is provided, detailed sensor information is returned.
  - When I(location_id) is provided without I(sensor_id), all sensors at that location are returned.
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
  sensor_id:
    description:
      - The ID of a specific sensor to retrieve detailed information for.
      - If omitted, returns all sensors at the specified I(location_id).
    type: int
  location_id:
    description:
      - Location ID to list sensors for.
      - Required when I(sensor_id) is not specified.
    type: int
"""

EXAMPLES = r"""
- name: Get all sensors at a location
  wyebot.wifi.wyebot_sensor_info:
    api_key: "{{ wyebot_api_key }}"
    location_id: 42
  register: location_sensors

- name: Get a specific sensor's details
  wyebot.wifi.wyebot_sensor_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: sensor

- name: Show offline sensors
  ansible.builtin.debug:
    msg: "Sensor {{ item.name }} is offline"
  loop: "{{ location_sensors.sensors }}"
  when: item.status != 'online'
"""

RETURN = r"""
sensors:
  description: List of Wyebot sensors.
  type: list
  elements: dict
  returned: always
  contains:
    id:
      description: Unique identifier for the sensor.
      type: int
      returned: always
      sample: 101
    name:
      description: Name assigned to the sensor.
      type: str
      returned: always
      sample: "Lobby Sensor"
    location_id:
      description: ID of the location where the sensor is deployed.
      type: int
      returned: always
      sample: 42
    status:
      description: Current operational status of the sensor.
      type: str
      returned: always
      sample: "online"
    model:
      description: Hardware model of the sensor.
      type: str
      returned: always
      sample: "WB-1000"
    firmware_version:
      description: Current firmware version running on the sensor.
      type: str
      returned: always
      sample: "3.2.1"
    ip_address:
      description: IP address of the sensor.
      type: str
      returned: always
      sample: "192.168.1.100"
    mac_address:
      description: MAC address of the sensor.
      type: str
      returned: always
      sample: "AA:BB:CC:DD:EE:FF"
  sample:
    - id: 101
      name: "Lobby Sensor"
      location_id: 42
      status: "online"
      model: "WB-1000"
      firmware_version: "3.2.1"
      ip_address: "192.168.1.100"
      mac_address: "AA:BB:CC:DD:EE:FF"
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
        sensor_id=dict(type='int'),
        location_id=dict(type='int'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[['sensor_id', 'location_id']],
    )

    client = WyebotAPI.from_module(module)

    try:
        sensor_id = module.params.get('sensor_id')
        location_id = module.params.get('location_id')

        if sensor_id is not None:
            result = client.get_sensor_info(sensor_id)
            sensors = [result] if isinstance(result, dict) else result
        else:
            result = client.get_sensors(location_id)
            sensors = result if isinstance(result, list) else result.get('sensors', [result])
    except WyebotAPIError as exc:
        module.fail_json(msg=str(exc))
        return

    module.exit_json(changed=False, sensors=sensors)


if __name__ == '__main__':
    main()
