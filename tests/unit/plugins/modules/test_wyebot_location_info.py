# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the wyebot_location_info module."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import patch

import pytest

from ansible_collections.wyebot.wifi.plugins.module_utils.wyebot_api import (
    WyebotAPIError,
)


MODULE_PATH = "ansible_collections.wyebot.wifi.plugins.modules.wyebot_location_info"


@pytest.fixture
def module_args_all(mock_module):
    """Module args for listing all locations (no location_id)."""
    mock_module.params["location_id"] = None
    return mock_module


@pytest.fixture
def module_args_single(mock_module):
    """Module args for retrieving a single location by ID."""
    mock_module.params["location_id"] = 1
    return mock_module


class TestWyebotLocationInfoList:
    """Tests for listing all locations."""

    def test_list_all_locations(self, mock_wyebot_api, sample_locations, module_args_all):
        """Successful retrieval of all locations returns the full list."""
        mock_wyebot_api.return_value = sample_locations

        with patch(f"{MODULE_PATH}.AnsibleModule") as mock_ansible_module:
            mock_ansible_module.return_value = module_args_all

            from ansible_collections.wyebot.wifi.plugins.modules import wyebot_location_info

            wyebot_location_info.main()

        module_args_all.exit_json.assert_called_once()
        call_kwargs = module_args_all.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert len(call_kwargs["locations"]) == 3
        assert call_kwargs["locations"][0]["name"] == "Main Office"

    def test_list_returns_empty_when_no_locations(self, mock_wyebot_api, module_args_all):
        """When the API returns an empty list, the module returns an empty list."""
        mock_wyebot_api.return_value = []

        with patch(f"{MODULE_PATH}.AnsibleModule") as mock_ansible_module:
            mock_ansible_module.return_value = module_args_all

            from ansible_collections.wyebot.wifi.plugins.modules import wyebot_location_info

            wyebot_location_info.main()

        call_kwargs = module_args_all.exit_json.call_args[1]
        assert call_kwargs["locations"] == []


class TestWyebotLocationInfoSingle:
    """Tests for retrieving a single location by ID."""

    def test_single_location_by_id(self, mock_wyebot_api, sample_locations, module_args_single):
        """When location_id is set, only the matching location is returned."""
        mock_wyebot_api.return_value = sample_locations

        with patch(f"{MODULE_PATH}.AnsibleModule") as mock_ansible_module:
            mock_ansible_module.return_value = module_args_single

            from ansible_collections.wyebot.wifi.plugins.modules import wyebot_location_info

            wyebot_location_info.main()

        call_kwargs = module_args_single.exit_json.call_args[1]
        assert len(call_kwargs["locations"]) == 1
        assert call_kwargs["locations"][0]["id"] == 1
        assert call_kwargs["locations"][0]["name"] == "Main Office"

    def test_single_location_not_found(self, mock_wyebot_api, sample_locations, mock_module):
        """When location_id does not match, an empty list is returned."""
        mock_module.params["location_id"] = 9999
        mock_wyebot_api.return_value = sample_locations

        with patch(f"{MODULE_PATH}.AnsibleModule") as mock_ansible_module:
            mock_ansible_module.return_value = mock_module

            from ansible_collections.wyebot.wifi.plugins.modules import wyebot_location_info

            wyebot_location_info.main()

        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["locations"] == []


class TestWyebotLocationInfoErrors:
    """Tests for API error handling."""

    def test_api_error_fails_module(self, mock_wyebot_api, module_args_all):
        """When WyebotAPIError is raised, the module calls fail_json."""
        mock_wyebot_api.side_effect = WyebotAPIError(
            "Wyebot API error 401 on /locations: Unauthorized",
            status_code=401,
        )

        with patch(f"{MODULE_PATH}.AnsibleModule") as mock_ansible_module:
            mock_ansible_module.return_value = module_args_all

            from ansible_collections.wyebot.wifi.plugins.modules import wyebot_location_info

            wyebot_location_info.main()

        module_args_all.fail_json.assert_called_once()
        fail_kwargs = module_args_all.fail_json.call_args[1]
        assert "401" in fail_kwargs["msg"]
        assert "Unauthorized" in fail_kwargs["msg"]

    def test_api_connection_error(self, mock_wyebot_api, module_args_all):
        """When WyebotAPIError for connection failure is raised, module fails."""
        mock_wyebot_api.side_effect = WyebotAPIError(
            "Failed to connect to Wyebot API at https://cloud.wyebot.com/api/v1/locations: "
            "Connection refused"
        )

        with patch(f"{MODULE_PATH}.AnsibleModule") as mock_ansible_module:
            mock_ansible_module.return_value = module_args_all

            from ansible_collections.wyebot.wifi.plugins.modules import wyebot_location_info

            wyebot_location_info.main()

        module_args_all.fail_json.assert_called_once()
        assert "Connection refused" in module_args_all.fail_json.call_args[1]["msg"]


class TestWyebotLocationInfoCheckMode:
    """Tests for check_mode behavior."""

    def test_check_mode_still_reads(self, mock_wyebot_api, sample_locations, mock_module):
        """In check_mode, read-only info modules still call the API and return data."""
        mock_module.check_mode = True
        mock_module.params["location_id"] = None
        mock_wyebot_api.return_value = sample_locations

        with patch(f"{MODULE_PATH}.AnsibleModule") as mock_ansible_module:
            mock_ansible_module.return_value = mock_module

            from ansible_collections.wyebot.wifi.plugins.modules import wyebot_location_info

            wyebot_location_info.main()

        # Info modules are read-only, so they execute even in check_mode
        mock_module.exit_json.assert_called_once()
        call_kwargs = mock_module.exit_json.call_args[1]
        assert call_kwargs["changed"] is False
        assert len(call_kwargs["locations"]) == 3
