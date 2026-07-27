# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Integration test fixtures: mock Wyebot API server.

Starts a lightweight HTTP server on a random port that serves mock JSON
responses for the Wyebot Cloud API endpoints.  The server runs in a
background thread and is torn down automatically after each test session.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import pytest


# ---------------------------------------------------------------------------
# Mock response data
# ---------------------------------------------------------------------------

MOCK_LOCATIONS = [
    {
        "id": 1,
        "name": "Integration Test Office",
        "address": "100 Test Blvd, Boston, MA 02101",
        "sensor_count": 2,
    },
    {
        "id": 2,
        "name": "Integration Test DC",
        "address": "200 Server Ln, Waltham, MA 02451",
        "sensor_count": 4,
    },
]

MOCK_SENSORS = [
    {
        "id": 201,
        "name": "integ-sensor-01",
        "mac": "11:22:33:44:55:01",
        "status": "online",
        "health_score": 91,
        "location_id": 1,
    },
    {
        "id": 202,
        "name": "integ-sensor-02",
        "mac": "11:22:33:44:55:02",
        "status": "online",
        "health_score": 78,
        "location_id": 1,
    },
]

MOCK_ALERTS = [
    {
        "id": 3001,
        "type": "rogue_ap",
        "severity": "high",
        "message": "Rogue AP detected during integration test",
        "sensor_id": 201,
        "timestamp": "2026-07-25T10:00:00Z",
    },
]

MOCK_NETWORK_TESTS = [
    {
        "id": 5001,
        "sensor_id": 201,
        "test_type": "throughput",
        "result": "pass",
        "value": 150.5,
        "unit": "Mbps",
        "timestamp": "2026-07-25T12:00:00Z",
    },
    {
        "id": 5002,
        "sensor_id": 201,
        "test_type": "latency",
        "result": "pass",
        "value": 12.3,
        "unit": "ms",
        "timestamp": "2026-07-25T12:00:00Z",
    },
]


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class MockWyebotHandler(BaseHTTPRequestHandler):
    """Handle POST requests mimicking the Wyebot Cloud API."""

    # Endpoint -> response data mapping
    ROUTES = {
        "/locations": MOCK_LOCATIONS,
        "/sensors": MOCK_SENSORS,
        "/alerts": MOCK_ALERTS,
        "/sensor/network_tests": MOCK_NETWORK_TESTS,
    }

    def do_POST(self):  # noqa: N802 — method name required by BaseHTTPRequestHandler
        """Route POST requests to mock responses."""
        # Read and discard request body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length:
            self.rfile.read(content_length)

        # Check API key header
        api_key = self.headers.get("X-API-Key", "")
        if not api_key:
            self._send_json({"error": "Missing API key"}, status=401)
            return

        # Route to mock data
        path = self.path.split("?")[0]  # strip query params if any
        if path in self.ROUTES:
            self._send_json(self.ROUTES[path])
        else:
            self._send_json({"error": "Not found"}, status=404)

    def _send_json(self, data, status=200):
        """Send a JSON response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Suppress request logging during tests."""
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _find_free_port():
    """Find and return a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def mock_api_server():
    """Start a mock Wyebot API server on a random port for the test session.

    Yields a dict with connection details::

        {
            "url": "http://127.0.0.1:<port>",
            "port": <port>,
            "api_key": "integration-test-key",
        }
    """
    port = _find_free_port()
    server = HTTPServer(("127.0.0.1", port), MockWyebotHandler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield {
        "url": f"http://127.0.0.1:{port}",
        "port": port,
        "api_key": "integration-test-key",
    }

    server.shutdown()
    thread.join(timeout=5)
