# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
    name: wyebot_api
    author:
      - Steve Fulmer (@stevefulmer)
    version_added: "1.0.0"
    short_description: Query the Wyebot Cloud API
    description:
      - This lookup plugin makes arbitrary calls to the Wyebot Cloud API.
      - Each term is an API method name corresponding to a method on the Wyebot API client
        (e.g. C(get_locations), C(get_sensors), C(get_alerts)).
      - Results are returned as a list of API response objects.
    options:
      _terms:
        description:
          - One or more API endpoint method names to call.
          - Supported methods include C(get_locations), C(get_sensors), C(get_network_tests),
            C(get_alerts), C(get_clients), C(get_access_points), and C(get_ssids).
        required: true
        type: list
        elements: str
      api_key:
        description:
          - API key for Wyebot Cloud authentication.
          - Falls back to the E(WYEBOT_API_KEY) environment variable.
        type: str
        required: true
        env:
          - name: WYEBOT_API_KEY
      api_url:
        description:
          - Base URL of the Wyebot Cloud API.
          - Falls back to the E(WYEBOT_API_URL) environment variable.
        type: str
        default: https://api.wyebot.com/api/v1
        env:
          - name: WYEBOT_API_URL
      validate_certs:
        description: Whether to validate SSL certificates.
        type: bool
        default: true
      timeout:
        description: HTTP request timeout in seconds.
        type: int
        default: 30
      data:
        description:
          - Dictionary of keyword arguments to pass to the API method.
          - For example, C({"location_id": 42}) for C(get_sensors) or
            C({"sensor_id": 1, "severity": "critical"}) for C(get_alerts).
        type: dict
        default: {}
    notes:
      - The lookup returns a list where each element is the result of one API call.
      - Each result is itself a list of dicts as returned by the Wyebot API.
    seealso:
      - module: wyebot.wifi.wyebot_sensor_info
      - module: wyebot.wifi.wyebot_location_info
"""

EXAMPLES = """
- name: Get all locations
  ansible.builtin.debug:
    msg: "{{ lookup('wyebot.wifi.wyebot_api', 'get_locations') }}"

- name: Get sensors for a specific location
  ansible.builtin.debug:
    msg: "{{ lookup('wyebot.wifi.wyebot_api', 'get_sensors', data={'location_id': 42}) }}"

- name: Get alerts with severity filter
  ansible.builtin.debug:
    msg: "{{ lookup('wyebot.wifi.wyebot_api', 'get_alerts', data={'severity': 'critical'}) }}"

- name: Get multiple endpoints in one lookup
  ansible.builtin.debug:
    msg: "{{ lookup('wyebot.wifi.wyebot_api', 'get_locations', 'get_alerts') }}"

- name: Use environment variables for authentication
  ansible.builtin.debug:
    msg: "{{ lookup('wyebot.wifi.wyebot_api', 'get_sensors') }}"
  environment:
    WYEBOT_API_KEY: "my-secret-key"

- name: Store results in a variable
  ansible.builtin.set_fact:
    wyebot_locations: "{{ lookup('wyebot.wifi.wyebot_api', 'get_locations') }}"
"""

RETURN = """
_list:
  description:
    - A list of API response objects.
    - Each element corresponds to one term and contains a list of dicts returned by the API.
  type: list
  elements: list
"""

import json
import os
from urllib.parse import urlencode, quote

from ansible.errors import AnsibleLookupError
from ansible.plugins.lookup import LookupBase
from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.utils.display import Display

display = Display()

SUPPORTED_METHODS = {
    "get_locations": {"endpoint": "/locations", "list_key": "locations", "params": ["location_id"]},
    "get_sensors": {"endpoint": "/sensors", "list_key": "sensors", "params": ["sensor_id", "location_id"]},
    "get_network_tests": {
        "endpoint": "/sensors/{sensor_id}/network-tests",
        "list_key": "tests",
        "params": ["sensor_id", "test_type", "limit"],
        "required": ["sensor_id"],
    },
    "get_alerts": {"endpoint": "/alerts", "list_key": "alerts", "params": ["location_id", "sensor_id", "severity", "limit"]},
    "get_clients": {
        "endpoint": "/sensors/{sensor_id}/clients",
        "list_key": "clients",
        "params": ["sensor_id", "mac_address", "ssid"],
        "required": ["sensor_id"],
    },
    "get_access_points": {
        "endpoint": "/sensors/{sensor_id}/access-points",
        "list_key": "access_points",
        "params": ["sensor_id", "bssid", "band"],
        "required": ["sensor_id"],
    },
    "get_ssids": {
        "endpoint": "/sensors/{sensor_id}/ssids",
        "list_key": "ssids",
        "params": ["sensor_id", "ssid_name"],
        "required": ["sensor_id"],
    },
}


class LookupModule(LookupBase):
    """Lookup plugin for querying the Wyebot Cloud API."""

    def _api_request(self, url, api_key, validate_certs, timeout):
        """Make an HTTP GET request to the Wyebot API.

        Args:
            url: Full URL to request.
            api_key: API key for authentication.
            validate_certs: Whether to validate SSL certificates.
            timeout: Request timeout in seconds.

        Returns:
            dict: Parsed JSON response.

        Raises:
            AnsibleLookupError: If the API request fails.
        """
        headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            display.vvv("Wyebot lookup API request: GET {0}".format(url))
            response = open_url(
                url,
                method="GET",
                headers=headers,
                validate_certs=validate_certs,
                timeout=timeout,
            )
            response_body = response.read()
            if response_body:
                return json.loads(response_body)
            return {}
        except HTTPError as e:
            raise AnsibleLookupError(
                "Wyebot API request failed: GET {0} returned HTTP {1}".format(url, e.code)
            )
        except URLError as e:
            raise AnsibleLookupError(
                "Failed to connect to Wyebot API at {0}: {1}".format(url, str(e.reason))
            )
        except Exception as e:
            raise AnsibleLookupError(
                "Unexpected error communicating with Wyebot API: {0}".format(str(e))
            )

    def _build_url(self, api_url, method_name, data):
        """Build the full API URL for a given method.

        Args:
            api_url: Base API URL.
            method_name: Name of the API method.
            data: Dict of parameters to pass.

        Returns:
            str: Full URL with query parameters.

        Raises:
            AnsibleLookupError: If the method is unknown or required params are missing.
        """
        if method_name not in SUPPORTED_METHODS:
            raise AnsibleLookupError(
                "Unknown Wyebot API method '{0}'. Supported methods: {1}".format(
                    method_name, ", ".join(sorted(SUPPORTED_METHODS.keys()))
                )
            )

        method_info = SUPPORTED_METHODS[method_name]
        endpoint = method_info["endpoint"]

        required_params = method_info.get("required", [])
        for param in required_params:
            if param not in data or data[param] is None:
                raise AnsibleLookupError(
                    "Method '{0}' requires the '{1}' parameter in data".format(method_name, param)
                )

        if "{sensor_id}" in endpoint:
            sensor_id = data.get("sensor_id")
            endpoint = endpoint.replace("{sensor_id}", str(sensor_id))

        if "{location_id}" in endpoint:
            location_id = data.get("location_id")
            endpoint = endpoint.replace("{location_id}", str(location_id))

        url = "{0}/{1}".format(api_url.rstrip("/"), endpoint.lstrip("/"))

        query_params = {}
        for param in method_info["params"]:
            if param in data and data[param] is not None:
                if "{" + param + "}" not in method_info["endpoint"]:
                    query_params[param] = data[param]

        if query_params:
            url = "{0}?{1}".format(url, urlencode(query_params))

        return url

    def _extract_results(self, response, method_name):
        """Extract the result list from an API response.

        Args:
            response: Parsed JSON response dict.
            method_name: Name of the API method called.

        Returns:
            list: List of result dicts.
        """
        list_key = SUPPORTED_METHODS[method_name]["list_key"]
        if isinstance(response, dict) and list_key in response:
            return response[list_key]
        if isinstance(response, list):
            return response
        return [response] if response else []

    def run(self, terms, variables=None, **kwargs):
        """Execute the lookup plugin.

        Args:
            terms: List of API method names to call.
            variables: Ansible variables available to the lookup.
            **kwargs: Additional keyword arguments (api_key, api_url, validate_certs, timeout, data).

        Returns:
            list: List of API response results, one per term.

        Raises:
            AnsibleLookupError: If authentication is missing or API calls fail.
        """
        self.set_options(var_options=variables, direct=kwargs)

        api_key = self.get_option("api_key")
        if not api_key:
            api_key = os.environ.get("WYEBOT_API_KEY")
        if not api_key:
            raise AnsibleLookupError(
                "Wyebot API key is required. Set via 'api_key' parameter or WYEBOT_API_KEY environment variable."
            )

        api_url = self.get_option("api_url")
        if not api_url:
            api_url = os.environ.get("WYEBOT_API_URL", "https://api.wyebot.com/api/v1")

        validate_certs = self.get_option("validate_certs")
        timeout = self.get_option("timeout")
        data = self.get_option("data") or {}

        results = []
        for term in terms:
            display.vvv("Wyebot lookup: calling method '{0}'".format(term))
            url = self._build_url(api_url, term, data)
            response = self._api_request(url, api_key, validate_certs, timeout)
            result = self._extract_results(response, term)
            results.append(result)

        return results
