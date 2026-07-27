# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2024 Wyebot, Inc.

"""
wyebot_prometheus - EDA event source plugin that scrapes a Wyebot Prometheus
exporter endpoint and fires events when metric values exceed configured
thresholds.
"""

DOCUMENTATION = r"""
---
module: wyebot_prometheus
short_description: Scrape Wyebot Prometheus exporter for threshold breaches
description:
  - Periodically scrapes a Prometheus-format metrics endpoint exposed by
    Wyebot infrastructure.
  - Compares each scraped metric value against user-defined thresholds and
    emits an event whenever a threshold is exceeded.
  - Parses the Prometheus text exposition format directly; no external
    Prometheus client library is required.
version_added: "1.0.0"
author:
  - Wyebot Collection Contributors
options:
  prometheus_url:
    description:
      - URL of the Prometheus metrics endpoint to scrape.
    type: str
    required: true
    default: "http://localhost:8014/metrics"
  poll_interval:
    description:
      - Number of seconds between scrape cycles.
    type: int
    default: 60
  thresholds:
    description:
      - Dictionary mapping metric names to their maximum acceptable value.
      - An event is emitted whenever a metric's value exceeds its threshold.
    type: dict
    required: true
  verify_ssl:
    description:
      - Whether to verify SSL/TLS certificates when scraping the endpoint.
    type: bool
    default: true
"""

EXAMPLES = r"""
- name: Alert on high client count and channel utilisation
  hosts: all
  sources:
    - wyebot.wifi.wyebot_prometheus:
        prometheus_url: "http://wyebot-exporter.example.com:8014/metrics"
        poll_interval: 60
        thresholds:
          wyebot_ap_client_count: 150
          wyebot_channel_utilization_percent: 85
  rules:
    - name: Metric threshold exceeded
      condition: event.wyebot.event_type == "metric_threshold"
      action:
        run_job_template:
          name: "WiFi Performance Remediation"
          organization: Default
          job_args:
            extra_vars:
              metric_name: "{{ event.wyebot.metric }}"
              metric_value: "{{ event.wyebot.value }}"
              threshold: "{{ event.wyebot.threshold }}"
"""

import asyncio
import logging
import re

try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

logger = logging.getLogger(__name__)

# Regex for parsing a single Prometheus text-format sample line.
# Matches: metric_name{label="value",...} value [timestamp]
_METRIC_RE = re.compile(
    r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)"
    r"(?:\{(?P<labels>[^}]*)\})?"
    r"\s+(?P<value>[^\s]+)"
    r"(?:\s+(?P<timestamp>\d+))?\s*$"
)


def _parse_labels(label_string: str) -> dict:
    """Parse a Prometheus label set string into a dict."""
    labels: dict = {}
    if not label_string:
        return labels
    for pair in label_string.split(","):
        pair = pair.strip()
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        labels[key.strip()] = value.strip().strip('"')
    return labels


def _parse_prometheus_text(text: str) -> list:
    """Parse Prometheus text exposition format into a list of samples.

    Each sample is a dict with keys: name, labels, value.
    Comment and TYPE/HELP lines are skipped.
    """
    samples = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _METRIC_RE.match(line)
        if not match:
            continue
        try:
            value = float(match.group("value"))
        except ValueError:
            continue
        samples.append(
            {
                "name": match.group("name"),
                "labels": _parse_labels(match.group("labels") or ""),
                "value": value,
            }
        )
    return samples


async def main(queue: asyncio.Queue, args: dict):
    """Scrape Prometheus metrics and enqueue threshold breach events."""

    if not HAS_AIOHTTP:
        raise ImportError(
            "The 'aiohttp' library is required for the wyebot_prometheus event source. "
            "Install it with: pip install aiohttp"
        )

    prometheus_url = args.get(
        "prometheus_url", "http://localhost:8014/metrics"
    )
    poll_interval = int(args.get("poll_interval", 60))
    thresholds = args.get("thresholds")
    verify_ssl = args.get("verify_ssl", True)

    if not thresholds or not isinstance(thresholds, dict):
        raise ValueError(
            "The 'thresholds' argument is required and must be a dict "
            "mapping metric names to maximum acceptable values."
        )

    ssl_context = None if verify_ssl else False

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_context),
    ) as session:
        while True:
            try:
                async with session.get(prometheus_url) as response:
                    response.raise_for_status()
                    text = await response.text()

                samples = _parse_prometheus_text(text)

                for sample in samples:
                    metric_name = sample["name"]
                    if metric_name not in thresholds:
                        continue
                    threshold = float(thresholds[metric_name])
                    if sample["value"] > threshold:
                        event = {
                            "wyebot": {
                                "event_type": "metric_threshold",
                                "metric": metric_name,
                                "value": sample["value"],
                                "threshold": threshold,
                                "labels": sample["labels"],
                            }
                        }
                        await queue.put(event)
                        logger.info(
                            "Threshold breach: %s=%.2f (max %.2f)",
                            metric_name,
                            sample["value"],
                            threshold,
                        )

            except aiohttp.ClientError as exc:
                logger.error(
                    "Error scraping Prometheus endpoint %s: %s",
                    prometheus_url,
                    exc,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Unexpected error in wyebot_prometheus: %s", exc
                )

            await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    import json

    class _MockQueue:
        async def put(self, item):
            print(json.dumps(item, indent=2))  # noqa: T201

    asyncio.run(
        main(
            _MockQueue(),
            {
                "prometheus_url": "http://localhost:8014/metrics",
                "thresholds": {"wyebot_ap_client_count": 100},
            },
        )
    )
