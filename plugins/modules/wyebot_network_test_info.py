#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_network_test_info
author: Steve Fulmer (@stevefulmer)
version_added: "1.0.0"
short_description: Retrieve Wyebot network test results.
description:
  - Get network test results from a Wyebot sensor.
  - Tests include DHCP, DNS, association, throughput, and other connectivity checks.
  - Results can be filtered by I(test_type) and limited by I(limit).
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
    description: The ID of the sensor to retrieve test results from.
    type: int
    required: true
  test_type:
    description:
      - Filter results by test type.
      - Common values include C(dhcp), C(dns), C(association), and C(throughput).
    type: str
    choices:
      - dhcp
      - dns
      - association
      - throughput
  limit:
    description: Maximum number of test results to return.
    type: int
    default: 10
"""

EXAMPLES = r"""
- name: Get recent network test results for a sensor
  wyebot.wifi.wyebot_network_test_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
  register: test_results

- name: Get DNS test results only
  wyebot.wifi.wyebot_network_test_info:
    api_key: "{{ wyebot_api_key }}"
    sensor_id: 101
    test_type: dns
    limit: 5
  register: dns_tests

- name: Alert on failed tests
  ansible.builtin.debug:
    msg: "FAILED: {{ item.test_type }} on sensor {{ item.sensor_id }}"
  loop: "{{ test_results.network_tests }}"
  when: item.status == 'fail'
"""

RETURN = r"""
network_tests:
  description: List of network test results.
  type: list
  elements: dict
  returned: always
  contains:
    sensor_id:
      description: ID of the sensor that ran the test.
      type: int
      returned: always
      sample: 101
    test_type:
      description: Type of network test performed.
      type: str
      returned: always
      sample: "dns"
    status:
      description: Result status of the test.
      type: str
      returned: always
      sample: "pass"
    timestamp:
      description: ISO 8601 timestamp of when the test was executed.
      type: str
      returned: always
      sample: "2025-01-15T10:30:00Z"
    details:
      description: Additional test-specific details and measurements.
      type: dict
      returned: always
      sample:
        response_time_ms: 12
        server: "8.8.8.8"
  sample:
    - sensor_id: 101
      test_type: "dns"
      status: "pass"
      timestamp: "2025-01-15T10:30:00Z"
      details:
        response_time_ms: 12
        server: "8.8.8.8"
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
        test_type=dict(
            type='str',
            choices=['dhcp', 'dns', 'association', 'throughput'],
        ),
        limit=dict(type='int', default=10),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = WyebotAPI.from_module(module)

    try:
        result = client.get_network_test_results(module.params['sensor_id'])
    except WyebotAPIError as exc:
        module.fail_json(msg=str(exc))
        return

    tests = result if isinstance(result, list) else result.get('tests', [result])

    # Client-side filtering by test_type
    test_type = module.params.get('test_type')
    if test_type is not None:
        tests = [t for t in tests if t.get('test_type') == test_type]

    # Client-side limit
    limit = module.params['limit']
    tests = tests[:limit]

    module.exit_json(changed=False, network_tests=tests)


if __name__ == '__main__':
    main()
