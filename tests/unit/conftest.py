# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared pytest fixtures for wyebot.wifi unit tests."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_module():
    """Return a mock AnsibleModule with common Wyebot auth parameters."""
    module = MagicMock()
    module.params = {
        "api_key": "test-api-key-12345",
        "api_url": "https://cloud.wyebot.com/api/v1",
        "validate_certs": True,
        "timeout": 30,
    }
    module.check_mode = False
    return module


@pytest.fixture
def mock_wyebot_api():
    """Patch WyebotAPI.request to return mock responses without HTTP calls.

    Yields a MagicMock whose ``return_value`` can be set per-test to control
    what the API client returns.

    Example::

        def test_locations(mock_wyebot_api, sample_locations):
            mock_wyebot_api.return_value = sample_locations
            # ... call module logic ...
    """
    with patch(
        "ansible_collections.wyebot.wifi.plugins.module_utils.wyebot_api.WyebotAPI.request"
    ) as mock_request:
        yield mock_request


@pytest.fixture
def sample_locations():
    """Return a list of sample Wyebot location dicts."""
    return [
        {
            "id": 1,
            "name": "Main Office",
            "address": "123 Main St, Boston, MA 02101",
            "sensor_count": 5,
        },
        {
            "id": 2,
            "name": "Branch Office",
            "address": "456 Oak Ave, Cambridge, MA 02139",
            "sensor_count": 3,
        },
        {
            "id": 3,
            "name": "Data Center",
            "address": "789 Tech Blvd, Waltham, MA 02451",
            "sensor_count": 8,
        },
    ]


@pytest.fixture
def sample_sensors():
    """Return a list of sample Wyebot sensor dicts."""
    return [
        {
            "id": 101,
            "name": "sensor-lobby-01",
            "mac": "AA:BB:CC:DD:EE:01",
            "status": "online",
            "health_score": 95,
            "location_id": 1,
        },
        {
            "id": 102,
            "name": "sensor-conf-02",
            "mac": "AA:BB:CC:DD:EE:02",
            "status": "online",
            "health_score": 87,
            "location_id": 1,
        },
        {
            "id": 103,
            "name": "sensor-dc-01",
            "mac": "AA:BB:CC:DD:EE:03",
            "status": "offline",
            "health_score": 0,
            "location_id": 3,
        },
    ]


@pytest.fixture
def sample_alerts():
    """Return a list of sample Wyebot alert dicts."""
    return [
        {
            "id": 1001,
            "type": "rogue_ap",
            "severity": "high",
            "message": "Rogue AP detected on channel 6",
            "sensor_id": 101,
            "timestamp": "2026-07-25T14:30:00Z",
        },
        {
            "id": 1002,
            "type": "interference",
            "severity": "medium",
            "message": "RF interference detected on 5 GHz band",
            "sensor_id": 102,
            "timestamp": "2026-07-25T15:00:00Z",
        },
        {
            "id": 1003,
            "type": "client_disconnect",
            "severity": "low",
            "message": "Multiple client disconnections in the last hour",
            "sensor_id": 101,
            "timestamp": "2026-07-25T15:30:00Z",
        },
    ]


@pytest.fixture
def sample_health():
    """Return a sample health data dict for a location."""
    return {
        "location_id": 1,
        "overall_score": 88,
        "network_scores": {
            "wifi_performance": 92,
            "client_experience": 85,
            "infrastructure_health": 90,
            "security": 83,
        },
    }
