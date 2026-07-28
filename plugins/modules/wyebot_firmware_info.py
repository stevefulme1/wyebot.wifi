#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_firmware_info
short_description: Get sensor firmware version information from Wyebot
version_added: "1.0.0"
description:
  - Retrieve firmware version information for Wyebot sensors.
  - Returns current version, latest available version, and whether
    an update is available for each sensor.
  - Can query a specific sensor or all sensors at a location.
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
    description: ID of a specific sensor to retrieve firmware info for.
    type: int
  location_id:
    description: >-
      ID of the location to retrieve firmware info for all sensors
      at that location.
    type: int
"""

EXAMPLES = r"""
- name: Get firmware info for a specific sensor
  wyebot.wifi.wyebot_firmware_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: sensor_firmware

- name: Get firmware info for all sensors at a location
  wyebot.wifi.wyebot_firmware_info:
    api_key: "{{ wyebot_api_key }}"
    location_id: 10
  register: location_firmware

- name: Report sensors needing updates
  ansible.builtin.debug:
    msg: >-
      Sensor {{ item.sensor_name }} ({{ item.sensor_id }}) needs update:
      {{ item.current_version }} -> {{ item.latest_version }}
  loop: "{{ location_firmware.firmware }}"
  when: item.update_available | default(false)
"""

RETURN = r"""
firmware:
  description: List of sensor firmware information.
  type: list
  elements: dict
  returned: always
  sample:
    - sensor_id: 101
      sensor_name: "Lobby Sensor"
      current_version: "3.5.1"
      latest_version: "3.6.0"
      update_available: true
      last_updated: "2024-01-10T08:00:00Z"
  contains:
    sensor_id:
      description: Unique identifier of the sensor.
      type: int
      returned: always
    sensor_name:
      description: Human-readable name of the sensor.
      type: str
      returned: always
    current_version:
      description: Currently installed firmware version.
      type: str
      returned: always
    latest_version:
      description: Latest available firmware version.
      type: str
      returned: always
    update_available:
      description: Whether a firmware update is available.
      type: bool
      returned: always
    last_updated:
      description: Timestamp of the last firmware update.
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
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)
    sensor_id = module.params.get("sensor_id")
    location_id = module.params.get("location_id")

    firmware_list = []

    try:
        if sensor_id is not None:
            result = client.get_firmware(sensor_id)
            fw = result.get("firmware", result) if isinstance(result, dict) else result
            if isinstance(fw, list):
                firmware_list = fw
            elif fw:
                firmware_list = [fw]
        elif location_id is not None:
            # Get all sensors at this location, then fetch firmware for each
            sensors_result = client.get_sensors(location_id)
            if isinstance(sensors_result, dict):
                sensors = sensors_result.get("sensors", sensors_result)
            else:
                sensors = sensors_result
            if not isinstance(sensors, list):
                sensors = [sensors] if sensors else []

            for sensor in sensors:
                sid = sensor.get("sensor_id", sensor.get("id"))
                if sid is None:
                    continue
                fw_result = client.get_firmware(sid)
                fw = fw_result.get("firmware", fw_result) if isinstance(fw_result, dict) else fw_result
                if isinstance(fw, list):
                    firmware_list.extend(fw)
                elif fw:
                    firmware_list.append(fw)
        else:
            module.fail_json(msg="One of sensor_id or location_id must be specified")
            return
    except WyebotAPIError as e:
        module.fail_json(
            msg="Failed to retrieve firmware data: {0}".format(str(e)),
            status_code=e.status_code,
        )
        return

    module.exit_json(changed=False, firmware=firmware_list)


if __name__ == "__main__":
    main()
