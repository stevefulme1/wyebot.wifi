#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: wyebot_api_key
short_description: Manage Wyebot API keys
version_added: "1.0.0"
description:
  - Create or revoke API keys for the Wyebot Cloud API.
  - When O(state=present), creates a new API key with the given name.
  - When O(state=absent), revokes the API key identified by O(key_id).
  - This module respects check mode for all mutations. In check mode,
    no API calls are made for create or revoke operations.
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
  state:
    description: Desired state of the API key.
    type: str
    choices:
      - present
      - absent
    default: present
  name:
    description: Name for the API key.
    type: str
    required: true
  key_id:
    description:
      - ID of the API key to revoke.
      - Required when O(state=absent).
    type: str
"""

EXAMPLES = r"""
- name: Create a new API key
  wyebot.wifi.wyebot_api_key:
    api_key: "{{ wyebot_admin_api_key }}"
    state: present
    name: "automation-key"
  register: new_key
  no_log: true

- name: Store the generated key securely
  ansible.builtin.debug:
    msg: "Key ID: {{ new_key.key_id }}"

- name: Revoke an API key
  wyebot.wifi.wyebot_api_key:
    api_key: "{{ wyebot_admin_api_key }}"
    state: absent
    name: "automation-key"
    key_id: "key-12345"

- name: Create API key in check mode
  wyebot.wifi.wyebot_api_key:
    api_key: "{{ wyebot_admin_api_key }}"
    state: present
    name: "test-key"
  check_mode: true
  register: check_result
"""

RETURN = r"""
key_id:
  description: Unique identifier of the API key.
  type: str
  returned: when state=present and not check mode
  sample: "key-12345"
name:
  description: Name of the API key.
  type: str
  returned: when state=present
  sample: "automation-key"
api_key_value:
  description: >-
    The generated API key value. Only returned on creation.
    Store this securely as it cannot be retrieved again.
  type: str
  returned: when state=present and not check mode
  sample: "wyebot_ak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
created_at:
  description: Timestamp when the API key was created.
  type: str
  returned: when state=present and not check mode
  sample: "2024-01-15T10:30:00Z"
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.wyebot.wifi.plugins.module_utils.wyebot_api import (
    WyebotAPI,
    WyebotAPIError,
    wyebot_argument_spec,
)


def create_api_key(module, client):
    """Create a new API key.

    Args:
        module: AnsibleModule instance.
        client: WyebotAPI client instance.

    Returns:
        dict: Result with key details.
    """
    name = module.params["name"]

    if module.check_mode:
        return dict(
            changed=True,
            name=name,
            msg="API key '{0}' would be created".format(name),
        )

    try:
        result = client.create_api_key(name=name)
    except WyebotAPIError as e:
        module.fail_json(
            msg="Failed to create API key: {0}".format(str(e)),
            status_code=e.status_code,
        )
        return

    return dict(
        changed=True,
        key_id=result.get("key_id", result.get("id", "")),
        name=name,
        api_key_value=result.get("api_key", result.get("key", "")),
        created_at=result.get("created_at", ""),
    )


def revoke_api_key(module, client):
    """Revoke an API key.

    Args:
        module: AnsibleModule instance.
        client: WyebotAPI client instance.

    Returns:
        dict: Result indicating whether revocation occurred.
    """
    key_id = module.params["key_id"]

    if module.check_mode:
        return dict(
            changed=True,
            msg="API key '{0}' would be revoked".format(key_id),
        )

    try:
        client.revoke_api_key(key_id=key_id)
    except WyebotAPIError as e:
        if e.status_code == 404:
            return dict(changed=False, msg="API key not found")
        module.fail_json(
            msg="Failed to revoke API key: {0}".format(str(e)),
            status_code=e.status_code,
        )
        return

    return dict(changed=True, msg="API key '{0}' revoked".format(key_id))


def main():
    """Entry point for module execution."""
    argument_spec = wyebot_argument_spec()
    argument_spec.update(dict(
        state=dict(type="str", choices=["present", "absent"], default="present"),
        name=dict(type="str", required=True),
        key_id=dict(type="str"),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            ("state", "absent", ["key_id"]),
        ],
    )

    client = WyebotAPI.from_module(module)
    state = module.params["state"]

    if state == "present":
        result = create_api_key(module, client)
        api_key_val = result.get("api_key_value", "")
        if api_key_val:
            module.no_log_values.add(api_key_val)
    else:
        result = revoke_api_key(module, client)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
