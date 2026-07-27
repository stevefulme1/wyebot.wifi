# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2024 Wyebot, Inc.

"""
wyebot_network_tests - EDA event source plugin that polls the Wyebot REST API
for network test results and fires events for test failures.
"""

DOCUMENTATION = r"""
---
module: wyebot_network_tests
short_description: Poll Wyebot API for network test failures
description:
  - Periodically polls the Wyebot REST API for network test results.
  - Emits events for test failures (or all results if C(fail_only) is
    C(false)).
  - Tracks the timestamp of the last poll so only new results are returned.
version_added: "1.0.0"
author:
  - Wyebot Collection Contributors
options:
  api_key:
    description:
      - API key for authenticating with the Wyebot REST API.
    type: str
    required: true
  api_url:
    description:
      - Base URL of the Wyebot REST API.
    type: str
    default: "https://cloud.wyebot.com/api/v1"
  poll_interval:
    description:
      - Number of seconds between polling cycles.
    type: int
    default: 120
  sensor_ids:
    description:
      - List of sensor IDs to poll.
      - When omitted, all sensors are polled.
    type: list
    elements: str
  test_types:
    description:
      - List of test types to include (e.g., C(dns), C(dhcp), C(ping),
        C(throughput)).
      - When omitted, all test types are returned.
    type: list
    elements: str
  fail_only:
    description:
      - When C(true) (the default), only failed tests generate events.
    type: bool
    default: true
  verify_ssl:
    description:
      - Whether to verify SSL/TLS certificates when connecting to the API.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Watch for DNS and DHCP test failures
  hosts: all
  sources:
    - wyebot.wifi.wyebot_network_tests:
        api_key: "{{ vault_wyebot_api_key }}"
        poll_interval: 120
        test_types:
          - dns
          - dhcp
        fail_only: true
  rules:
    - name: Network test failed
      condition: event.wyebot.event_type == "test_failure"
      action:
        run_job_template:
          name: "Investigate Network Test Failure"
          organization: Default
          job_args:
            extra_vars:
              test_type: "{{ event.wyebot.test_type }}"
              sensor_id: "{{ event.wyebot.sensor_id }}"

- name: Poll specific sensors for all test results
  hosts: all
  sources:
    - wyebot.wifi.wyebot_network_tests:
        api_key: "{{ vault_wyebot_api_key }}"
        sensor_ids:
          - sensor-001
          - sensor-002
        fail_only: false
        poll_interval: 300
  rules:
    - name: Log every test result
      condition: event.wyebot.event_type == "test_failure"
      action:
        debug:
          msg: "Test result: {{ event.wyebot.test }}"
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

logger = logging.getLogger(__name__)


async def main(queue: asyncio.Queue, args: dict):
    """Poll Wyebot for network test results and enqueue failure events."""

    if not HAS_AIOHTTP:
        raise ImportError(
            "The 'aiohttp' library is required for the wyebot_network_tests "
            "event source. Install it with: pip install aiohttp"
        )

    api_key = args.get("api_key")
    if not api_key:
        raise ValueError("The 'api_key' argument is required.")

    api_url = args.get("api_url", "https://cloud.wyebot.com/api/v1").rstrip("/")
    poll_interval = int(args.get("poll_interval", 120))
    sensor_ids = args.get("sensor_ids")
    test_types = args.get("test_types")
    fail_only = args.get("fail_only", True)
    verify_ssl = args.get("verify_ssl", True)

    if sensor_ids and not isinstance(sensor_ids, list):
        sensor_ids = [sensor_ids]
    if test_types and not isinstance(test_types, list):
        test_types = [test_types]

    last_poll_ts = datetime.now(timezone.utc).isoformat()

    headers = {
        "X-API-Key": api_key,
        "Accept": "application/json",
    }

    ssl_context = None if verify_ssl else False

    async with aiohttp.ClientSession(
        headers=headers,
        connector=aiohttp.TCPConnector(ssl=ssl_context),
    ) as session:
        while True:
            try:
                params: dict = {"since": last_poll_ts}
                current_poll_ts = datetime.now(timezone.utc).isoformat()

                targets = sensor_ids if sensor_ids else [None]
                for sid in targets:
                    url = f"{api_url}/network-tests"
                    if sid:
                        params["sensor_id"] = sid

                    async with session.post(url, json=params) as response:
                        response.raise_for_status()
                        data = await response.json()

                    results = (
                        data
                        if isinstance(data, list)
                        else data.get("results", data.get("tests", []))
                    )

                    for test in results:
                        test_type = str(
                            test.get("test_type", test.get("type", ""))
                        ).lower()
                        if test_types and test_type not in [
                            t.lower() for t in test_types
                        ]:
                            continue

                        status = str(test.get("status", "")).lower()
                        if fail_only and status not in (
                            "fail",
                            "failed",
                            "error",
                        ):
                            continue

                        event = {
                            "wyebot": {
                                "event_type": "test_failure",
                                "test": test,
                                "sensor_id": test.get("sensor_id", sid or ""),
                                "test_type": test_type,
                            }
                        }
                        await queue.put(event)
                        logger.info(
                            "Enqueued test_failure sensor=%s type=%s",
                            test.get("sensor_id", sid),
                            test_type,
                        )

                last_poll_ts = current_poll_ts

            except aiohttp.ClientError as exc:
                logger.error("Error polling Wyebot API: %s", exc)
            except json.JSONDecodeError as exc:
                logger.error(
                    "Invalid JSON response from Wyebot API: %s", exc
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Unexpected error in wyebot_network_tests: %s", exc
                )

            await asyncio.sleep(poll_interval)


if __name__ == "__main__":

    class _MockQueue:
        async def put(self, item):
            print(json.dumps(item, indent=2))  # noqa: T201

    asyncio.run(main(_MockQueue(), {"api_key": "test"}))
