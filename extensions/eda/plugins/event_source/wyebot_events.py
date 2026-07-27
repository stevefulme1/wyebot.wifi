# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2024 Wyebot, Inc.

"""
wyebot_events - EDA event source plugin that polls the Wyebot REST API for
alerts and events, placing them onto the EDA event queue for rule evaluation.
"""

DOCUMENTATION = r"""
---
module: wyebot_events
short_description: Poll Wyebot REST API for alerts and events
description:
  - Continuously polls the Wyebot REST API for new alerts and events.
  - Tracks previously seen alert IDs to avoid duplicate events.
  - Supports filtering by location, sensor, and severity level.
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
    default: 30
  location_id:
    description:
      - Limit alerts to a specific Wyebot location ID.
    type: str
  sensor_id:
    description:
      - Limit alerts to a specific Wyebot sensor ID.
    type: str
  severity_filter:
    description:
      - List of severity levels to include (e.g., C(critical), C(warning), C(info)).
      - When omitted, all severities are returned.
    type: list
    elements: str
  verify_ssl:
    description:
      - Whether to verify SSL/TLS certificates when connecting to the API.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Poll Wyebot for all alerts
  hosts: all
  sources:
    - wyebot.wifi.wyebot_events:
        api_key: "{{ vault_wyebot_api_key }}"
        poll_interval: 30
  rules:
    - name: Log every alert
      condition: event.wyebot.event_type == "alert"
      action:
        debug:
          msg: "Alert received: {{ event.wyebot.alert }}"

- name: Poll only critical alerts for a specific sensor
  hosts: all
  sources:
    - wyebot.wifi.wyebot_events:
        api_key: "{{ vault_wyebot_api_key }}"
        api_url: "https://wyebot.example.com/api/v1"
        sensor_id: "sensor-001"
        severity_filter:
          - critical
        poll_interval: 15
        verify_ssl: true
  rules:
    - name: Handle critical alert
      condition: event.wyebot.event_type == "alert"
      action:
        run_job_template:
          name: "Remediate Critical WiFi Alert"
          organization: Default
"""

import asyncio
import json
import logging

try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

logger = logging.getLogger(__name__)


async def main(queue: asyncio.Queue, args: dict):
    """Poll the Wyebot REST API for alerts and enqueue new events."""

    if not HAS_AIOHTTP:
        raise ImportError(
            "The 'aiohttp' library is required for the wyebot_events event source. "
            "Install it with: pip install aiohttp"
        )

    api_key = args.get("api_key")
    if not api_key:
        raise ValueError("The 'api_key' argument is required.")

    api_url = args.get("api_url", "https://cloud.wyebot.com/api/v1").rstrip("/")
    poll_interval = int(args.get("poll_interval", 30))
    location_id = args.get("location_id")
    sensor_id = args.get("sensor_id")
    severity_filter = args.get("severity_filter")
    verify_ssl = args.get("verify_ssl", True)

    if severity_filter and not isinstance(severity_filter, list):
        severity_filter = [severity_filter]

    from collections import OrderedDict

    _MAX_SEEN = 10000
    seen_alert_ids: dict = OrderedDict()

    def _track_seen(alert_id):
        seen_alert_ids[alert_id] = None
        while len(seen_alert_ids) > _MAX_SEEN:
            seen_alert_ids.popitem(last=False)

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
                params: dict = {}
                if location_id:
                    params["location_id"] = location_id
                if sensor_id:
                    params["sensor_id"] = sensor_id

                url = f"{api_url}/alerts"
                async with session.post(url, json=params) as response:
                    response.raise_for_status()
                    data = await response.json()

                alerts = data if isinstance(data, list) else data.get("alerts", [])

                for alert in alerts:
                    alert_id = alert.get("id") or alert.get("alert_id")
                    if alert_id and alert_id in seen_alert_ids:
                        continue

                    alert_severity = str(
                        alert.get("severity", "")
                    ).lower()
                    if severity_filter and alert_severity not in [
                        s.lower() for s in severity_filter
                    ]:
                        continue

                    if alert_id:
                        _track_seen(alert_id)

                    event = {
                        "wyebot": {
                            "event_type": "alert",
                            "alert": alert,
                            "sensor_id": alert.get("sensor_id", sensor_id or ""),
                            "location_id": alert.get(
                                "location_id", location_id or ""
                            ),
                        }
                    }
                    await queue.put(event)
                    logger.info(
                        "Enqueued alert id=%s severity=%s",
                        alert_id,
                        alert_severity,
                    )

            except aiohttp.ClientError as exc:
                logger.error("Error polling Wyebot API: %s", exc)
            except json.JSONDecodeError as exc:
                logger.error("Invalid JSON response from Wyebot API: %s", exc)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Unexpected error in wyebot_events: %s", exc)

            await asyncio.sleep(poll_interval)


if __name__ == "__main__":

    class _MockQueue:
        """Minimal queue for local testing."""

        async def put(self, item):
            print(json.dumps(item, indent=2))  # noqa: T201

    asyncio.run(main(_MockQueue(), {"api_key": "test"}))
