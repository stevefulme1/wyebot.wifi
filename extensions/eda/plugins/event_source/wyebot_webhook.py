# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2024 Wyebot, Inc.

"""
wyebot_webhook - EDA event source plugin that starts an HTTP server to receive
webhook notifications from Wyebot, with optional HMAC signature verification
and TLS support.
"""

DOCUMENTATION = r"""
---
module: wyebot_webhook
short_description: HTTP webhook receiver for Wyebot notifications
description:
  - Starts an HTTP server that listens for POST requests on C(/webhook).
  - Validates an optional HMAC signature header for webhook authenticity.
  - Supports TLS via user-supplied certificate and key files.
  - Forwards the parsed JSON payload as an EDA event.
version_added: "1.0.0"
author:
  - Wyebot Collection Contributors
options:
  host:
    description:
      - IP address on which the webhook server listens.
    type: str
    default: "0.0.0.0"
  port:
    description:
      - TCP port on which the webhook server listens.
    type: int
    default: 5000
  token:
    description:
      - Optional bearer token for simple webhook authentication.
      - When set, the server rejects requests that do not include a matching
        C(Authorization) header.
    type: str
  hmac_secret:
    description:
      - Shared secret used to verify HMAC-SHA256 signatures on incoming
        webhook payloads.
    type: str
  hmac_header:
    description:
      - HTTP header containing the HMAC-SHA256 signature.
    type: str
    default: "X-Wyebot-Signature"
  ssl_cert:
    description:
      - Path to a PEM-encoded TLS certificate file.
    type: str
  ssl_key:
    description:
      - Path to a PEM-encoded TLS private key file.
    type: str
"""

EXAMPLES = r"""
- name: Listen for Wyebot webhooks on default port
  hosts: all
  sources:
    - wyebot.wifi.wyebot_webhook:
        port: 5000
  rules:
    - name: Process incoming webhook
      condition: event.wyebot.event_type == "webhook"
      action:
        debug:
          msg: "Webhook received: {{ event.wyebot.payload }}"

- name: Secured webhook receiver with HMAC and TLS
  hosts: all
  sources:
    - wyebot.wifi.wyebot_webhook:
        host: "0.0.0.0"
        port: 8443
        hmac_secret: "{{ vault_webhook_hmac_secret }}"
        hmac_header: "X-Wyebot-Signature"
        ssl_cert: "/etc/pki/tls/certs/webhook.pem"
        ssl_key: "/etc/pki/tls/private/webhook.key"
  rules:
    - name: Handle webhook event
      condition: event.wyebot.event_type == "webhook"
      action:
        run_job_template:
          name: "Process Wyebot Webhook"
          organization: Default
"""

import asyncio
import hashlib
import hmac
import json
import logging
import ssl as ssl_mod

try:
    from aiohttp import web

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

logger = logging.getLogger(__name__)


def _verify_hmac(secret: str, body: bytes, signature: str) -> bool:
    """Verify an HMAC-SHA256 signature against the request body."""
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    # Support signatures with or without a "sha256=" prefix.
    if signature.startswith("sha256="):
        signature = signature[7:]
    return hmac.compare_digest(expected.lower(), signature.lower())


async def main(queue: asyncio.Queue, args: dict):
    """Start an HTTP webhook server and enqueue incoming events."""

    if not HAS_AIOHTTP:
        raise ImportError(
            "The 'aiohttp' library is required for the wyebot_webhook event "
            "source. Install it with: pip install aiohttp"
        )

    host = args.get("host", "0.0.0.0")
    port = int(args.get("port", 5000))
    token = args.get("token")
    hmac_secret = args.get("hmac_secret")
    hmac_header = args.get("hmac_header", "X-Wyebot-Signature")
    ssl_cert = args.get("ssl_cert")
    ssl_key = args.get("ssl_key")

    async def _handle_webhook(request: web.Request) -> web.Response:
        """Handle an incoming POST to /webhook."""
        # Bearer token validation
        if token:
            auth = request.headers.get("Authorization", "")
            if not hmac.compare_digest(auth, f"Bearer {token}"):
                logger.warning("Webhook rejected: invalid bearer token")
                return web.Response(status=401, text="Unauthorized")

        body = await request.read()

        # HMAC validation
        if hmac_secret:
            signature = request.headers.get(hmac_header, "")
            if not signature:
                logger.warning(
                    "Webhook rejected: missing HMAC header %s", hmac_header
                )
                return web.Response(
                    status=401, text="Missing signature header"
                )
            if not _verify_hmac(hmac_secret, body, signature):
                logger.warning("Webhook rejected: invalid HMAC signature")
                return web.Response(status=401, text="Invalid signature")

        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            logger.error("Webhook received non-JSON body")
            return web.Response(status=400, text="Invalid JSON")

        # Build a sanitised header dict (exclude hop-by-hop headers).
        header_dict = {
            k: v
            for k, v in request.headers.items()
            if k.lower()
            not in (
                "host",
                "content-length",
                "transfer-encoding",
                "authorization",
                hmac_header.lower() if hmac_header else "",
            )
        }

        event = {
            "wyebot": {
                "event_type": "webhook",
                "payload": payload,
                "headers": header_dict,
            }
        }
        await queue.put(event)
        logger.info("Enqueued webhook event")
        return web.Response(status=200, text="OK")

    async def _health(request: web.Request) -> web.Response:
        """Simple health-check endpoint."""
        return web.Response(status=200, text="OK")

    app = web.Application()
    app.router.add_post("/webhook", _handle_webhook)
    app.router.add_get("/health", _health)

    ssl_context = None
    if ssl_cert and ssl_key:
        ssl_context = ssl_mod.SSLContext(ssl_mod.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(ssl_cert, ssl_key)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
    logger.info("Starting webhook server on %s:%d", host, port)
    await site.start()

    # Block forever so the event source keeps running.
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()


if __name__ == "__main__":

    class _MockQueue:
        async def put(self, item):
            print(json.dumps(item, indent=2))  # noqa: T201

    asyncio.run(main(_MockQueue(), {"port": 5000}))
