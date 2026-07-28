# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
    name: wyebot
    author:
      - Steve Fulmer (@stevefulmer)
    version_added: "1.0.0"
    short_description: Wyebot dynamic inventory plugin
    description:
      - Queries the Wyebot Cloud API for locations and sensors.
      - Creates host entries for each sensor with connection and metadata variables.
      - Supports grouping by location, sensor status, and sensor model.
      - Supports the Ansible constructed features for composing host variables and keyed groups.
      - Supports caching via the Ansible cache framework.
    options:
      plugin:
        description: Token that ensures this is a source file for the C(wyebot.wifi.wyebot) plugin.
        required: true
        choices: ['wyebot.wifi.wyebot']
      api_key:
        description:
          - API key for Wyebot Cloud authentication.
          - Can also be set via the E(WYEBOT_API_KEY) environment variable.
        required: true
        type: str
        env:
          - name: WYEBOT_API_KEY
      api_url:
        description:
          - Base URL of the Wyebot Cloud API.
          - Can also be set via the E(WYEBOT_API_URL) environment variable.
        required: false
        type: str
        default: https://api.wyebot.com/api/v1
        env:
          - name: WYEBOT_API_URL
      validate_certs:
        description: Whether to validate SSL certificates when connecting to the API.
        required: false
        type: bool
        default: true
      timeout:
        description: HTTP request timeout in seconds.
        required: false
        type: int
        default: 30
      group_by:
        description:
          - List of attributes to create groups by.
          - Valid values are C(location), C(status), and C(model).
        required: false
        type: list
        elements: str
        default:
          - location
          - status
          - model
      compose:
        description:
          - Dictionary of composed host variables using Jinja2 expressions.
          - Keys are variable names, values are Jinja2 templates.
        required: false
        type: dict
        default: {}
      keyed_groups:
        description:
          - List of keyed group definitions for constructed groups.
          - Each entry is a dict with C(key), optional C(prefix), C(separator), and C(parent_group).
        required: false
        type: list
        elements: dict
        default: []
      strict:
        description:
          - If C(true), raise an error on any Jinja2 expression failure in C(compose) or C(keyed_groups).
          - If C(false), failures in expressions are silently ignored.
        required: false
        type: bool
        default: false
    extends_documentation_fragment:
      - constructed
      - inventory_cache
    requirements:
      - A valid Wyebot Cloud API key.
"""

EXAMPLES = """
# Minimal inventory file (wyebot.yml or mycloud.wyebot.yaml)
---
plugin: wyebot.wifi.wyebot
api_key: "my-secret-api-key"

# Full example with all options
plugin: wyebot.wifi.wyebot
api_key: "my-secret-api-key"
api_url: "https://api.wyebot.com/api/v1"
validate_certs: true
timeout: 30
group_by:
  - location
  - status
  - model
compose:
  wyebot_display_name: "wyebot_location_name ~ ' / ' ~ inventory_hostname"
  is_online: "wyebot_status == 'online'"
keyed_groups:
  - key: wyebot_firmware
    prefix: firmware
    separator: "_"
strict: false

# Using environment variables for credentials
---
plugin: wyebot.wifi.wyebot
# api_key read from WYEBOT_API_KEY environment variable
group_by:
  - location
"""

import json
from urllib.parse import urlencode

from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable
from ansible.module_utils.urls import open_url
from ansible.module_utils.six.moves.urllib.error import HTTPError, URLError
from ansible.utils.display import Display

display = Display()


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    """Wyebot dynamic inventory plugin.

    Queries the Wyebot Cloud API for locations and sensors and creates
    Ansible inventory host entries for each discovered sensor.
    """

    NAME = "wyebot.wifi.wyebot"

    def __init__(self):
        super(InventoryModule, self).__init__()
        self._api_key = None
        self._api_url = None
        self._validate_certs = True
        self._timeout = 30

    def verify_file(self, path):
        """Verify that the inventory source file is valid for this plugin.

        Args:
            path: Path to the inventory source file.

        Returns:
            bool: True if the file is valid for this plugin.
        """
        valid = False
        if super(InventoryModule, self).verify_file(path):
            if path.endswith((".wyebot.yml", ".wyebot.yaml")):
                valid = True
            else:
                display.vvv(
                    "Skipping {0}, does not end with .wyebot.yml or .wyebot.yaml".format(path)
                )
        return valid

    def _api_request(self, endpoint, params=None):
        """Make an HTTP GET request to the Wyebot API.

        Args:
            endpoint: API endpoint path (e.g. /locations).
            params: Optional dict of query parameters.

        Returns:
            dict: Parsed JSON response.

        Raises:
            AnsibleParserError: If the API request fails.
        """
        url = "{0}/{1}".format(self._api_url, endpoint.lstrip("/"))

        if params:
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                url = "{0}?{1}".format(url, urlencode(filtered))

        headers = {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            display.vvv("Wyebot API request: GET {0}".format(url))
            response = open_url(
                url,
                method="GET",
                headers=headers,
                validate_certs=self._validate_certs,
                timeout=self._timeout,
            )
            response_body = response.read()
            if response_body:
                return json.loads(response_body)
            return {}
        except HTTPError as e:
            raise AnsibleParserError(
                "Wyebot API request failed: GET {0} returned HTTP {1}".format(url, e.code)
            )
        except URLError as e:
            raise AnsibleParserError(
                "Failed to connect to Wyebot API at {0}: {1}".format(url, str(e.reason))
            )
        except Exception as e:
            raise AnsibleParserError(
                "Unexpected error communicating with Wyebot API: {0}".format(str(e))
            )

    def _fetch_locations(self):
        """Fetch all locations from the Wyebot API.

        Returns:
            list: List of location dicts.
        """
        result = self._api_request("/locations")
        if isinstance(result, dict) and "locations" in result:
            return result["locations"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def _fetch_sensors(self, location_id=None):
        """Fetch sensors from the Wyebot API.

        Args:
            location_id: Optional location ID to filter sensors.

        Returns:
            list: List of sensor dicts.
        """
        params = {}
        if location_id is not None:
            params["location_id"] = location_id

        result = self._api_request("/sensors", params=params or None)
        if isinstance(result, dict) and "sensors" in result:
            return result["sensors"]
        if isinstance(result, list):
            return result
        return [result] if result else []

    def _sanitize_group_name(self, name):
        """Sanitize a string for use as an Ansible group name.

        Replaces non-alphanumeric characters with underscores and lowercases the result.

        Args:
            name: The raw group name string.

        Returns:
            str: A sanitized group name safe for Ansible.
        """
        sanitized = ""
        for char in str(name):
            if char.isalnum() or char == "_":
                sanitized += char
            else:
                sanitized += "_"
        return sanitized.strip("_").lower()

    def _populate_from_api(self):
        """Query the Wyebot API and return the inventory data structure.

        Returns:
            dict: Inventory data with locations and sensors.
        """
        inventory_data = {"locations": [], "sensors": []}

        locations = self._fetch_locations()
        inventory_data["locations"] = locations

        location_map = {}
        for location in locations:
            loc_id = location.get("id") or location.get("location_id")
            loc_name = location.get("name") or location.get("location_name", "unknown")
            if loc_id is not None:
                location_map[loc_id] = loc_name

        for location in locations:
            loc_id = location.get("id") or location.get("location_id")
            if loc_id is not None:
                sensors = self._fetch_sensors(location_id=loc_id)
                for sensor in sensors:
                    sensor["_location_id"] = loc_id
                    sensor["_location_name"] = location_map.get(loc_id, "unknown")
                    inventory_data["sensors"].append(sensor)

        if not locations:
            sensors = self._fetch_sensors()
            for sensor in sensors:
                loc_id = sensor.get("location_id")
                sensor["_location_id"] = loc_id
                sensor["_location_name"] = location_map.get(loc_id, "unknown") if loc_id else "unknown"
                inventory_data["sensors"].append(sensor)

        return inventory_data

    def _populate_inventory(self, inventory_data):
        """Populate the Ansible inventory from the fetched data.

        Args:
            inventory_data: Dict containing locations and sensors from the API.
        """
        group_by = self.get_option("group_by")
        strict = self.get_option("strict")

        self.inventory.add_group("wyebot_sensors")

        for sensor in inventory_data.get("sensors", []):
            sensor_id = sensor.get("id") or sensor.get("sensor_id")
            sensor_name = sensor.get("name") or sensor.get("hostname") or "sensor_{0}".format(sensor_id)
            sensor_status = sensor.get("status", "unknown")
            sensor_model = sensor.get("model", "unknown")
            sensor_firmware = sensor.get("firmware") or sensor.get("firmware_version", "")
            sensor_ip = sensor.get("ip") or sensor.get("ip_address", "")
            sensor_mac = sensor.get("mac") or sensor.get("mac_address", "")
            location_id = sensor.get("_location_id")
            location_name = sensor.get("_location_name", "unknown")

            hostname = self._sanitize_group_name(sensor_name)
            if not hostname:
                hostname = "sensor_{0}".format(sensor_id)

            self.inventory.add_host(hostname, group="wyebot_sensors")

            self.inventory.set_variable(hostname, "wyebot_sensor_id", sensor_id)
            self.inventory.set_variable(hostname, "wyebot_location_id", location_id)
            self.inventory.set_variable(hostname, "wyebot_location_name", location_name)
            self.inventory.set_variable(hostname, "wyebot_status", sensor_status)
            self.inventory.set_variable(hostname, "wyebot_model", sensor_model)
            self.inventory.set_variable(hostname, "wyebot_firmware", sensor_firmware)
            self.inventory.set_variable(hostname, "wyebot_ip", sensor_ip)
            self.inventory.set_variable(hostname, "wyebot_mac", sensor_mac)

            if sensor_ip:
                self.inventory.set_variable(hostname, "ansible_host", sensor_ip)

            if "location" in group_by and location_name:
                group_name = "location_{0}".format(self._sanitize_group_name(location_name))
                self.inventory.add_group(group_name)
                self.inventory.add_child(group_name, hostname)

            if "status" in group_by and sensor_status:
                group_name = "status_{0}".format(self._sanitize_group_name(sensor_status))
                self.inventory.add_group(group_name)
                self.inventory.add_child(group_name, hostname)

            if "model" in group_by and sensor_model:
                group_name = "model_{0}".format(self._sanitize_group_name(sensor_model))
                self.inventory.add_group(group_name)
                self.inventory.add_child(group_name, hostname)

            self._set_composite_vars(
                self.get_option("compose"),
                self.inventory.get_host(hostname).get_vars(),
                hostname,
                strict=strict,
            )

            self._add_host_to_keyed_groups(
                self.get_option("keyed_groups"),
                self.inventory.get_host(hostname).get_vars(),
                hostname,
                strict=strict,
            )

    def parse(self, inventory, loader, path, cache=True):
        """Parse the inventory source and populate the inventory.

        Args:
            inventory: Ansible inventory object.
            loader: Ansible data loader.
            path: Path to the inventory source file.
            cache: Whether to use caching.
        """
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)

        self._api_key = self.get_option("api_key")
        self._api_url = self.get_option("api_url").rstrip("/")
        self._validate_certs = self.get_option("validate_certs")
        self._timeout = self.get_option("timeout")

        cache_key = self.get_cache_key(path)
        user_cache_setting = self.get_option("cache")
        attempt_to_read_cache = user_cache_setting and cache
        cache_needs_update = user_cache_setting and not cache

        inventory_data = None

        if attempt_to_read_cache:
            try:
                inventory_data = self._cache[cache_key]
                display.vvv("Wyebot inventory loaded from cache")
            except KeyError:
                display.vvv("Wyebot inventory cache miss, fetching from API")
                cache_needs_update = True

        if inventory_data is None:
            inventory_data = self._populate_from_api()

        if cache_needs_update:
            self._cache[cache_key] = inventory_data

        self._populate_inventory(inventory_data)
