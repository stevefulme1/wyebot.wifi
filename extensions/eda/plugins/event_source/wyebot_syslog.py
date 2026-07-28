# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2024 Wyebot, Inc.

"""
wyebot_syslog - EDA event source plugin that listens for syslog messages from
Wyebot infrastructure using asyncio UDP or TCP transports, parses them
according to RFC 5424, and enqueues structured events.
"""

DOCUMENTATION = r"""
---
module: wyebot_syslog
short_description: Parse Wyebot syslog messages via UDP or TCP
description:
  - Listens on a UDP or TCP socket for syslog messages from Wyebot
    infrastructure.
  - Parses messages according to RFC 5424 syslog format.
  - Supports filtering by syslog facility and severity.
version_added: "1.0.0"
author:
  - Wyebot Collection Contributors
options:
  host:
    description:
      - IP address on which the syslog server listens.
    type: str
    default: "0.0.0.0"
  port:
    description:
      - Port on which the syslog server listens.
    type: int
    default: 514
  protocol:
    description:
      - Transport protocol.
    type: str
    default: "udp"
    choices:
      - udp
      - tcp
  facility_filter:
    description:
      - List of syslog facility names to include (e.g., C(local0), C(kern)).
      - When omitted, all facilities are accepted.
    type: list
    elements: str
  severity_filter:
    description:
      - List of syslog severity names to include (e.g., C(emerg), C(alert),
        C(crit), C(err), C(warning)).
      - When omitted, all severities are accepted.
    type: list
    elements: str
"""

EXAMPLES = r"""
- name: Listen for Wyebot syslog on UDP 514
  hosts: all
  sources:
    - wyebot.wifi.wyebot_syslog:
        host: "0.0.0.0"
        port: 514
        protocol: udp
  rules:
    - name: Process syslog message
      condition: event.wyebot.event_type == "syslog"
      action:
        debug:
          msg: >-
            Syslog from {{ event.wyebot.hostname }}:
            {{ event.wyebot.message }}

- name: Listen for critical syslog via TCP
  hosts: all
  sources:
    - wyebot.wifi.wyebot_syslog:
        host: "0.0.0.0"
        port: 1514
        protocol: tcp
        severity_filter:
          - emerg
          - alert
          - crit
          - err
        facility_filter:
          - local0
          - local1
  rules:
    - name: Critical syslog event
      condition: event.wyebot.event_type == "syslog"
      action:
        run_job_template:
          name: "Investigate Syslog Alert"
          organization: Default
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# RFC 5424 facility codes
_FACILITIES = [
    "kern", "user", "mail", "daemon", "auth", "syslog", "lpr", "news",
    "uucp", "cron", "authpriv", "ftp", "ntp", "audit", "alert", "clock",
    "local0", "local1", "local2", "local3", "local4", "local5", "local6",
    "local7",
]

# RFC 5424 severity codes
_SEVERITIES = [
    "emerg", "alert", "crit", "err", "warning", "notice", "info", "debug",
]

# Regex for RFC 5424 header: <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID
_RFC5424_RE = re.compile(
    r"<(?P<pri>\d{1,3})>"
    r"(?P<version>\d)?\s*"
    r"(?P<timestamp>\S+)\s+"
    r"(?P<hostname>\S+)\s+"
    r"(?P<appname>\S+)\s+"
    r"(?P<procid>\S+)\s+"
    r"(?P<msgid>\S+)\s*"
    r"(?P<msg>.*)"
)

# Fallback regex for BSD-style (RFC 3164) messages: <PRI>TIMESTAMP HOSTNAME MSG
_RFC3164_RE = re.compile(
    r"<(?P<pri>\d{1,3})>"
    r"(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<hostname>\S+)\s+"
    r"(?P<msg>.*)"
)


def _decode_priority(pri: int) -> tuple:
    """Decode a syslog PRI value into facility and severity names."""
    facility_idx = pri >> 3
    severity_idx = pri & 0x07
    facility = (
        _FACILITIES[facility_idx]
        if facility_idx < len(_FACILITIES)
        else f"unknown({facility_idx})"
    )
    severity = (
        _SEVERITIES[severity_idx]
        if severity_idx < len(_SEVERITIES)
        else f"unknown({severity_idx})"
    )
    return facility, severity


def _parse_syslog(data: str) -> dict | None:
    """Parse a syslog message string into a structured dict."""
    data = data.strip()
    if not data:
        return None

    match = _RFC5424_RE.match(data)
    if match:
        pri = int(match.group("pri"))
        facility, severity = _decode_priority(pri)
        return {
            "facility": facility,
            "severity": severity,
            "timestamp": match.group("timestamp"),
            "hostname": match.group("hostname"),
            "appname": match.group("appname"),
            "procid": match.group("procid"),
            "msgid": match.group("msgid"),
            "message": match.group("msg").strip(),
        }

    match = _RFC3164_RE.match(data)
    if match:
        pri = int(match.group("pri"))
        facility, severity = _decode_priority(pri)
        return {
            "facility": facility,
            "severity": severity,
            "timestamp": match.group("timestamp"),
            "hostname": match.group("hostname"),
            "appname": "-",
            "procid": "-",
            "msgid": "-",
            "message": match.group("msg").strip(),
        }

    # Last resort: treat entire string as the message.
    return {
        "facility": "unknown",
        "severity": "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": "-",
        "appname": "-",
        "procid": "-",
        "msgid": "-",
        "message": data,
    }


async def main(queue: asyncio.Queue, args: dict):
    """Start a syslog listener and enqueue parsed events."""

    host = args.get("host", "0.0.0.0")
    port = int(args.get("port", 514))
    protocol = args.get("protocol", "udp").lower()
    facility_filter = args.get("facility_filter")
    severity_filter = args.get("severity_filter")

    if facility_filter and not isinstance(facility_filter, list):
        facility_filter = [facility_filter]
    if severity_filter and not isinstance(severity_filter, list):
        severity_filter = [severity_filter]

    if facility_filter:
        facility_filter = [f.lower() for f in facility_filter]
    if severity_filter:
        severity_filter = [s.lower() for s in severity_filter]

    async def _process_message(data: str):
        """Parse and optionally filter a syslog message, then enqueue."""
        parsed = _parse_syslog(data)
        if parsed is None:
            return

        if facility_filter and parsed["facility"] not in facility_filter:
            return
        if severity_filter and parsed["severity"] not in severity_filter:
            return

        event = {
            "wyebot": {
                "event_type": "syslog",
                "facility": parsed["facility"],
                "severity": parsed["severity"],
                "message": parsed["message"],
                "hostname": parsed["hostname"],
                "timestamp": parsed["timestamp"],
            }
        }
        await queue.put(event)
        logger.debug(
            "Enqueued syslog event from %s severity=%s",
            parsed["hostname"],
            parsed["severity"],
        )

    if protocol == "udp":

        class _SyslogUDPProtocol(asyncio.DatagramProtocol):
            def __init__(self, message_handler):
                self._handler = message_handler
                self._loop = asyncio.get_event_loop()

            def datagram_received(self, data: bytes, addr):
                try:
                    message = data.decode("utf-8", errors="replace")
                except Exception:  # noqa: BLE001
                    return
                asyncio.ensure_future(self._handler(message))

        transport, _protocol = await asyncio.get_event_loop().create_datagram_endpoint(
            lambda: _SyslogUDPProtocol(_process_message),
            local_addr=(host, port),
        )
        logger.info("Syslog UDP listener started on %s:%d", host, port)

        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            transport.close()

    elif protocol == "tcp":

        async def _handle_tcp_client(
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter,
        ):
            peer = writer.get_extra_info("peername")
            logger.debug("Syslog TCP connection from %s", peer)
            max_line_bytes = 65536
            try:
                while True:
                    data = await reader.readline()
                    if not data:
                        break
                    if len(data) > max_line_bytes:
                        logger.warning(
                            "Syslog TCP line from %s exceeded %d bytes, "
                            "truncating",
                            peer,
                            max_line_bytes,
                        )
                        data = data[:max_line_bytes]
                    message = data.decode("utf-8", errors="replace")
                    await _process_message(message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.error("Error handling TCP client %s: %s", peer, exc)
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:  # noqa: BLE001
                    pass

        server = await asyncio.start_server(
            _handle_tcp_client, host, port
        )
        logger.info("Syslog TCP listener started on %s:%d", host, port)

        async with server:
            await server.serve_forever()

    else:
        raise ValueError(
            f"Unsupported protocol '{protocol}'. Use 'udp' or 'tcp'."
        )


if __name__ == "__main__":

    class _MockQueue:
        async def put(self, item):
            print(json.dumps(item, indent=2))  # noqa: T201

    asyncio.run(main(_MockQueue(), {"port": 1514, "protocol": "udp"}))
