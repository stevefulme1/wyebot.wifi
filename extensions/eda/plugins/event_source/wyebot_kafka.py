# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2024 Wyebot, Inc.

"""
wyebot_kafka - EDA event source plugin that consumes Wyebot events from an
Apache Kafka topic, deserialises JSON message values, and enqueues them for
EDA rule processing.
"""

DOCUMENTATION = r"""
---
module: wyebot_kafka
short_description: Consume Wyebot events from Apache Kafka
description:
  - Connects to an Apache Kafka cluster and consumes messages from a
    configured topic.
  - Deserialises message values as JSON and wraps them in the standard
    Wyebot event envelope.
  - Supports SASL authentication and TLS for secure Kafka clusters.
  - Automatically reconnects on transient errors.
version_added: "1.0.0"
author:
  - Wyebot Collection Contributors
options:
  bootstrap_servers:
    description:
      - Comma-separated list of Kafka broker addresses.
    type: str
    required: true
  topic:
    description:
      - Kafka topic to consume from.
    type: str
    default: "wyebot-events"
  group_id:
    description:
      - Kafka consumer group ID.
    type: str
    default: "ansible-eda-wyebot"
  auto_offset_reset:
    description:
      - Where to start consuming when no committed offset exists.
      - Choices are C(latest) or C(earliest).
    type: str
    default: "latest"
  security_protocol:
    description:
      - Kafka security protocol.
    type: str
    default: "PLAINTEXT"
    choices:
      - PLAINTEXT
      - SSL
      - SASL_PLAINTEXT
      - SASL_SSL
  sasl_mechanism:
    description:
      - SASL authentication mechanism (e.g., C(PLAIN), C(SCRAM-SHA-256),
        C(SCRAM-SHA-512)).
    type: str
  sasl_username:
    description:
      - Username for SASL authentication.
    type: str
    no_log: true
  sasl_password:
    description:
      - Password for SASL authentication.
    type: str
    no_log: true
  ssl_cafile:
    description:
      - Path to a CA certificate file for TLS verification.
    type: str
"""

EXAMPLES = r"""
- name: Consume events from a plaintext Kafka cluster
  hosts: all
  sources:
    - wyebot.wifi.wyebot_kafka:
        bootstrap_servers: "kafka1:9092,kafka2:9092"
        topic: "wyebot-events"
        group_id: "ansible-eda-wyebot"
  rules:
    - name: Handle Kafka event
      condition: event.wyebot.event_type == "kafka"
      action:
        debug:
          msg: "Kafka event: {{ event.wyebot.payload }}"

- name: Consume from a SASL-authenticated Kafka cluster
  hosts: all
  sources:
    - wyebot.wifi.wyebot_kafka:
        bootstrap_servers: "kafka.example.com:9093"
        topic: "wyebot-alerts"
        security_protocol: "SASL_SSL"
        sasl_mechanism: "SCRAM-SHA-512"
        sasl_username: "{{ vault_kafka_username }}"
        sasl_password: "{{ vault_kafka_password }}"
        ssl_cafile: "/etc/pki/tls/certs/kafka-ca.pem"
  rules:
    - name: Route Kafka alert
      condition: event.wyebot.event_type == "kafka"
      action:
        run_job_template:
          name: "Process Wyebot Kafka Alert"
          organization: Default
"""

import asyncio
import json
import logging

try:
    from aiokafka import AIOKafkaConsumer  # type: ignore[import-untyped]

    HAS_AIOKAFKA = True
except ImportError:
    HAS_AIOKAFKA = False

logger = logging.getLogger(__name__)


async def main(queue: asyncio.Queue, args: dict):
    """Consume Kafka messages and enqueue Wyebot events."""

    if not HAS_AIOKAFKA:
        raise ImportError(
            "The 'aiokafka' library is required for the wyebot_kafka event "
            "source. Install it with: pip install aiokafka"
        )

    bootstrap_servers = args.get("bootstrap_servers")
    if not bootstrap_servers:
        raise ValueError("The 'bootstrap_servers' argument is required.")

    topic = args.get("topic", "wyebot-events")
    group_id = args.get("group_id", "ansible-eda-wyebot")
    auto_offset_reset = args.get("auto_offset_reset", "latest")
    security_protocol = args.get("security_protocol", "PLAINTEXT")
    sasl_mechanism = args.get("sasl_mechanism")
    sasl_username = args.get("sasl_username")
    sasl_password = args.get("sasl_password")
    ssl_cafile = args.get("ssl_cafile")

    consumer_kwargs: dict = {
        "bootstrap_servers": bootstrap_servers,
        "group_id": group_id,
        "auto_offset_reset": auto_offset_reset,
        "security_protocol": security_protocol,
        "enable_auto_commit": True,
        "value_deserializer": lambda m: m,  # raw bytes; we decode below
    }
    if sasl_mechanism:
        consumer_kwargs["sasl_mechanism"] = sasl_mechanism
    if sasl_username:
        consumer_kwargs["sasl_plain_username"] = sasl_username
    if sasl_password:
        consumer_kwargs["sasl_plain_password"] = sasl_password
    if ssl_cafile:
        consumer_kwargs["ssl_cafile"] = ssl_cafile

    while True:
        consumer = None
        try:
            consumer = AIOKafkaConsumer(topic, **consumer_kwargs)
            await consumer.start()
            logger.info(
                "Connected to Kafka topic=%s group=%s", topic, group_id
            )

            async for msg in consumer:
                try:
                    payload = json.loads(msg.value.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    logger.warning(
                        "Skipping non-JSON Kafka message at "
                        "partition=%s offset=%s: %s",
                        msg.partition,
                        msg.offset,
                        exc,
                    )
                    continue

                event = {
                    "wyebot": {
                        "event_type": "kafka",
                        "topic": msg.topic,
                        "partition": msg.partition,
                        "offset": msg.offset,
                        "payload": payload,
                    }
                }
                await queue.put(event)
                logger.debug(
                    "Enqueued Kafka event topic=%s partition=%d offset=%d",
                    msg.topic,
                    msg.partition,
                    msg.offset,
                )

        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Kafka consumer error (will reconnect in 10s): %s", exc
            )
            await asyncio.sleep(10)
        finally:
            if consumer:
                try:
                    await consumer.stop()
                except Exception:  # noqa: BLE001
                    pass


if __name__ == "__main__":

    class _MockQueue:
        async def put(self, item):
            print(json.dumps(item, indent=2))  # noqa: T201

    asyncio.run(
        main(
            _MockQueue(),
            {"bootstrap_servers": "localhost:9092"},
        )
    )
