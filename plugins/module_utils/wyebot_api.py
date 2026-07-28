# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Steve Fulmer <sfulmer@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared REST API client for the Wyebot WiFi monitoring platform.

All Wyebot API calls use HTTP POST with JSON payloads. Authentication is
performed via an ``X-API-Key`` header. This module provides a single
:class:`WyebotAPI` client used by every module in the collection, plus a
:func:`wyebot_argument_spec` helper that returns the common auth parameters
so individual modules stay DRY.
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
import time

from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.module_utils.urls import open_url


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class WyebotAPIError(Exception):
    """Raised when the Wyebot API returns an error or is unreachable."""

    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


# ---------------------------------------------------------------------------
# Argument spec helper
# ---------------------------------------------------------------------------

def wyebot_argument_spec():
    """Return the common Ansible argument_spec dict for Wyebot auth params.

    Every module in the collection should merge this into its own
    ``argument_spec`` so the auth interface stays consistent::

        argument_spec = wyebot_argument_spec()
        argument_spec.update(dict(
            location_id=dict(type='int', required=True),
        ))
    """
    return dict(
        api_key=dict(type='str', required=True, no_log=True),
        api_url=dict(
            type='str',
            default='https://cloud.wyebot.com/api/v1',
        ),
        validate_certs=dict(type='bool', default=True),
        timeout=dict(type='int', default=30),
    )


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class WyebotAPI:
    """REST client for the Wyebot Cloud API.

    Parameters
    ----------
    api_key : str
        Wyebot API key (sent as ``X-API-Key`` header).
    api_url : str
        Base URL for the API, without a trailing slash.
    validate_certs : bool
        Whether to verify the server TLS certificate.
    timeout : int
        HTTP request timeout in seconds.
    check_mode : bool
        When ``True``, mutating methods (create/revoke API key) return
        immediately without making a real request.

    Usage from an Ansible module::

        from ansible_collections.wyebot.wifi.plugins.module_utils.wyebot_api import (
            WyebotAPI, WyebotAPIError, wyebot_argument_spec,
        )

        def main():
            argument_spec = wyebot_argument_spec()
            argument_spec.update(dict(
                location_id=dict(type='int', required=True),
            ))
            module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

            client = WyebotAPI.from_module(module)
            try:
                result = client.get_sensors(module.params['location_id'])
            except WyebotAPIError as exc:
                module.fail_json(msg=str(exc))

            module.exit_json(changed=False, sensors=result)
    """

    # Retry settings for 429 Too Many Requests
    _MAX_RETRIES = 3
    _BACKOFF_BASE = 2  # seconds; exponential: 2, 4, 8

    def __init__(self, api_key, api_url='https://cloud.wyebot.com/api/v1',
                 validate_certs=True, timeout=30, check_mode=False):
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.validate_certs = validate_certs
        self.timeout = timeout
        self.check_mode = check_mode

    # ------------------------------------------------------------------
    # Convenience constructor
    # ------------------------------------------------------------------

    @classmethod
    def from_module(cls, module):
        """Build a :class:`WyebotAPI` from an ``AnsibleModule`` instance.

        Reads ``api_key``, ``api_url``, ``validate_certs``, ``timeout``,
        and ``check_mode`` from the module parameters / state.
        """
        return cls(
            api_key=module.params['api_key'],
            api_url=module.params.get('api_url', 'https://cloud.wyebot.com/api/v1'),
            validate_certs=module.params.get('validate_certs', True),
            timeout=module.params.get('timeout', 30),
            check_mode=module.check_mode,
        )

    # ------------------------------------------------------------------
    # Low-level HTTP
    # ------------------------------------------------------------------

    def request(self, endpoint, data=None):
        """Send a POST request to *endpoint* and return the parsed JSON body.

        Parameters
        ----------
        endpoint : str
            API path relative to *api_url* (leading ``/`` optional).
        data : dict or None
            JSON payload to include in the POST body.  ``None`` sends an
            empty JSON object ``{}``.

        Returns
        -------
        dict
            Parsed JSON response.

        Raises
        ------
        WyebotAPIError
            On HTTP errors, network errors, or non-JSON responses.
        """
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint

        url = self.api_url + endpoint

        payload = json.dumps(data or {}).encode('utf-8')

        headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        last_exc = None
        for attempt in range(self._MAX_RETRIES + 1):
            try:
                resp = open_url(
                    url,
                    data=payload,
                    headers=headers,
                    method='POST',
                    timeout=self.timeout,
                    validate_certs=self.validate_certs,
                )
                body = resp.read().decode('utf-8')
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    raise WyebotAPIError(
                        "Wyebot API returned non-JSON response from {0}".format(endpoint),
                        status_code=resp.getcode(),
                        response_body=body,
                    )
            except HTTPError as exc:
                if exc.code == 429 and attempt < self._MAX_RETRIES:
                    # Rate limited -- back off and retry
                    retry_after = exc.headers.get('Retry-After')
                    if retry_after and retry_after.isdigit():
                        wait = int(retry_after)
                    else:
                        wait = self._BACKOFF_BASE ** (attempt + 1)
                    time.sleep(wait)
                    last_exc = exc
                    continue

                error_body = ''
                try:
                    error_body = exc.read().decode('utf-8')
                except Exception:
                    pass
                truncated_body = (error_body[:256] + '...') if len(error_body) > 256 else error_body
                raise WyebotAPIError(
                    "Wyebot API error {0} on {1}: {2}".format(
                        exc.code, endpoint, truncated_body or exc.reason,
                    ),
                    status_code=exc.code,
                    response_body=error_body,
                ) from exc
            except URLError as exc:
                raise WyebotAPIError(
                    "Failed to connect to Wyebot API at {0}: {1}".format(
                        url, exc.reason,
                    ),
                ) from exc

        # Should not reach here, but handle gracefully
        raise WyebotAPIError(
            "Wyebot API request to {0} failed after {1} retries".format(
                endpoint, self._MAX_RETRIES,
            ),
            status_code=getattr(last_exc, 'code', None),
        )

    # ------------------------------------------------------------------
    # Read-only endpoints (safe in check_mode)
    # ------------------------------------------------------------------

    def get_locations(self):
        """Return a list of all Wyebot locations."""
        return self.request('/locations')

    def get_sensors(self, location_id):
        """Return sensors at the given location.

        Parameters
        ----------
        location_id : int
            Wyebot location identifier.
        """
        return self.request('/sensors', data={'location_id': location_id})

    def get_sensor_info(self, sensor_id):
        """Return detailed information for a single sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/info', data={'sensor_id': sensor_id})

    def get_network_test_results(self, sensor_id):
        """Return network test results for a sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/network_tests', data={'sensor_id': sensor_id})

    def get_alerts(self, location_id=None, sensor_id=None):
        """Return alerts, optionally filtered by location or sensor.

        Parameters
        ----------
        location_id : int or None
            Filter alerts to this location.
        sensor_id : int or None
            Filter alerts to this sensor.
        """
        payload = {}
        if location_id is not None:
            payload['location_id'] = location_id
        if sensor_id is not None:
            payload['sensor_id'] = sensor_id
        return self.request('/alerts', data=payload)

    def get_clients(self, sensor_id):
        """Return WiFi clients visible to a sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/clients', data={'sensor_id': sensor_id})

    def get_aps(self, sensor_id):
        """Return access points visible to a sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/aps', data={'sensor_id': sensor_id})

    def get_ssids(self, sensor_id):
        """Return SSIDs detected by a sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/ssids', data={'sensor_id': sensor_id})

    def get_channels(self, sensor_id):
        """Return channel utilization data for a sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/channels', data={'sensor_id': sensor_id})

    def get_interference(self, sensor_id):
        """Return RF interference data for a sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/interference', data={'sensor_id': sensor_id})

    def get_rogue_aps(self, sensor_id):
        """Return rogue access points detected by a sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/rogue_aps', data={'sensor_id': sensor_id})

    def get_spectrum(self, sensor_id):
        """Return spectrum analysis data for a sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/spectrum', data={'sensor_id': sensor_id})

    def get_health(self, sensor_id):
        """Return health metrics for a sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/health', data={'sensor_id': sensor_id})

    def get_firmware(self, sensor_id):
        """Return firmware information for a sensor.

        Parameters
        ----------
        sensor_id : int
            Wyebot sensor identifier.
        """
        return self.request('/sensor/firmware', data={'sensor_id': sensor_id})

    # ------------------------------------------------------------------
    # Mutating endpoints (skipped in check_mode)
    # ------------------------------------------------------------------

    def create_api_key(self, name):
        """Create a new API key.

        Parameters
        ----------
        name : str
            Human-readable label for the new key.

        Returns
        -------
        dict
            Response containing the new key details, or an empty dict
            in check_mode.
        """
        if self.check_mode:
            return {}
        return self.request('/api_key/create', data={'name': name})

    def revoke_api_key(self, key_id):
        """Revoke an existing API key.

        Parameters
        ----------
        key_id : str
            Identifier of the key to revoke.

        Returns
        -------
        dict
            Response confirming revocation, or an empty dict in check_mode.
        """
        if self.check_mode:
            return {}
        return self.request('/api_key/revoke', data={'key_id': key_id})
