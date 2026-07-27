#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_location_info
author: Steve Fulmer (@stevefulmer)
version_added: "1.0.0"
short_description: Retrieve Wyebot location information.
description:
  - Get information about one or all Wyebot locations.
  - When I(location_id) is specified, returns details for that single location.
  - When I(location_id) is omitted, returns all locations visible to the API key.
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
  location_id:
    description:
      - The ID of a specific location to retrieve.
      - If omitted, all locations are returned.
    type: int
"""

EXAMPLES = r"""
- name: Get all Wyebot locations
  wyebot.wifi.wyebot_location_info:
    api_key: "{{ wyebot_api_key }}"
  register: all_locations

- name: Get a specific location
  wyebot.wifi.wyebot_location_info:
    api_key: "{{ wyebot_api_key }}"
    location_id: 42
  register: location

- name: Display location names
  ansible.builtin.debug:
    msg: "{{ item.name }}"
  loop: "{{ all_locations.locations }}"
"""

RETURN = r"""
locations:
  description: List of Wyebot locations.
  type: list
  elements: dict
  returned: always
  contains:
    id:
      description: Unique identifier for the location.
      type: int
      returned: always
      sample: 42
    name:
      description: Name of the location.
      type: str
      returned: always
      sample: "Main Office"
    address:
      description: Physical address of the location.
      type: str
      returned: always
      sample: "123 Main St, Boston, MA 02101"
    sensor_count:
      description: Number of sensors deployed at this location.
      type: int
      returned: always
      sample: 5
  sample:
    - id: 42
      name: "Main Office"
      address: "123 Main St, Boston, MA 02101"
      sensor_count: 5
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
        location_id=dict(type='int'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)

    try:
        result = client.get_locations()
    except WyebotAPIError as exc:
        module.fail_json(msg=str(exc))
        return

    locations = result if isinstance(result, list) else result.get('locations', [result])

    location_id = module.params.get('location_id')
    if location_id is not None:
        locations = [loc for loc in locations if loc.get('id') == location_id]

    module.exit_json(changed=False, locations=locations)


if __name__ == '__main__':
    main()
