#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_spectrum_info
short_description: Get spectrum analysis data from Wyebot sensors
version_added: "1.0.0"
description:
  - Retrieve spectrum analysis data from Wyebot wireless sensors.
  - Returns data including noise floor averages, peak interference,
    channel utilization map, and non-WiFi interference sources.
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
    description: ID of the sensor to retrieve spectrum data from.
    type: int
    required: true
  band:
    description:
      - Filter spectrum data by wireless band.
      - When the API returns per-band data, only the matching band is returned.
    type: str
    choices:
      - 2.4GHz
      - 5GHz
      - 6GHz
  time_range_minutes:
    description: Time range in minutes for spectrum analysis data.
    type: int
    default: 60
"""

EXAMPLES = r"""
- name: Get spectrum analysis data for a sensor
  wyebot.wifi.wyebot_spectrum_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: spectrum_data

- name: Get 5GHz spectrum data for the last 2 hours
  wyebot.wifi.wyebot_spectrum_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    band: "5GHz"
    time_range_minutes: 120
  register: spectrum_5ghz

- name: Display spectrum analysis results
  ansible.builtin.debug:
    msg: >-
      Band: {{ spectrum_data.spectrum.band }},
      Avg noise floor: {{ spectrum_data.spectrum.avg_noise_floor }}dBm,
      Non-WiFi sources: {{ spectrum_data.spectrum.non_wifi_interference_sources | length }}
"""

RETURN = r"""
spectrum:
  description: Spectrum analysis data.
  type: dict
  returned: always
  sample:
    band: "2.4GHz"
    avg_noise_floor: -95
    peak_interference: -72
    channel_utilization_map:
      "1": 35.2
      "6": 67.8
      "11": 22.1
    non_wifi_interference_sources:
      - "microwave_oven"
      - "bluetooth"
  contains:
    band:
      description: Wireless band analyzed.
      type: str
      returned: always
    avg_noise_floor:
      description: Average noise floor in dBm across the band.
      type: int
      returned: always
    peak_interference:
      description: Peak interference level in dBm.
      type: int
      returned: always
    channel_utilization_map:
      description: >-
        Dictionary mapping channel numbers to their utilization percentage.
      type: dict
      returned: always
    non_wifi_interference_sources:
      description: List of detected non-WiFi interference source types.
      type: list
      elements: str
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
        time_range_minutes=dict(type="int", default=60),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)

    try:
        result = client.get_spectrum(module.params["sensor_id"])
    except WyebotAPIError as e:
        module.fail_json(
            msg="Failed to retrieve spectrum data: {0}".format(str(e)),
            status_code=e.status_code,
        )
        return

    spectrum = result.get("spectrum", result) if isinstance(result, dict) else result
    if not isinstance(spectrum, dict):
        spectrum = {}

    band = module.params.get("band")
    if band and isinstance(spectrum.get("bands"), list):
        for band_data in spectrum["bands"]:
            if band_data.get("band") == band:
                spectrum = band_data
                break

    module.exit_json(changed=False, spectrum=spectrum)


if __name__ == "__main__":
    main()
