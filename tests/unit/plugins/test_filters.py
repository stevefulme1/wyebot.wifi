# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for wyebot.wifi filter plugins."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible.errors import AnsibleFilterError


# ---------------------------------------------------------------------------
# wyebot_health_level tests
# ---------------------------------------------------------------------------


class TestWyebotHealthLevel:
    """Tests for the wyebot_health_level filter."""

    @pytest.mark.parametrize(
        "score, expected",
        [
            (0, "critical"),
            (20, "critical"),
            (39, "critical"),
            (40, "warning"),
            (55, "warning"),
            (69, "warning"),
            (70, "good"),
            (85, "good"),
            (89, "good"),
            (90, "excellent"),
            (95, "excellent"),
            (100, "excellent"),
        ],
    )
    def test_health_level_boundaries(self, score, expected):
        """Health level classification at boundary values."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import (
            wyebot_health_level,
        )

        assert wyebot_health_level(score) == expected

    def test_health_level_accepts_string_number(self):
        """Health level accepts string representation of a number."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import (
            wyebot_health_level,
        )

        assert wyebot_health_level("75") == "good"

    def test_health_level_invalid_input_raises(self):
        """Health level raises AnsibleFilterError on non-numeric input."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import (
            wyebot_health_level,
        )

        with pytest.raises(AnsibleFilterError, match="requires a numeric score"):
            wyebot_health_level("not-a-number")


# ---------------------------------------------------------------------------
# wyebot_health_color tests
# ---------------------------------------------------------------------------


class TestWyebotHealthColor:
    """Tests for the wyebot_health_color filter."""

    @pytest.mark.parametrize(
        "score, expected",
        [
            (10, "red"),
            (39, "red"),
            (40, "yellow"),
            (69, "yellow"),
            (70, "green"),
            (100, "green"),
        ],
    )
    def test_health_color_boundaries(self, score, expected):
        """Health color classification at boundary values."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import (
            wyebot_health_color,
        )

        assert wyebot_health_color(score) == expected

    def test_health_color_invalid_input_raises(self):
        """Health color raises AnsibleFilterError on non-numeric input."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import (
            wyebot_health_color,
        )

        with pytest.raises(AnsibleFilterError, match="requires a numeric score"):
            wyebot_health_color(None)


# ---------------------------------------------------------------------------
# wyebot_health_threshold tests
# ---------------------------------------------------------------------------


class TestWyebotHealthThreshold:
    """Tests for the wyebot_health_threshold filter."""

    def test_threshold_filters_below_default(self):
        """Items with score below default threshold (70) are returned."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import (
            wyebot_health_threshold,
        )

        data = [
            {"name": "sensor-1", "score": 92},
            {"name": "sensor-2", "score": 65},
            {"name": "sensor-3", "score": 78},
        ]
        result = wyebot_health_threshold(data)
        assert len(result) == 1
        assert result[0]["name"] == "sensor-2"

    def test_threshold_custom_min_score(self):
        """Custom min_score parameter changes the threshold."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import (
            wyebot_health_threshold,
        )

        data = [
            {"name": "sensor-1", "score": 92},
            {"name": "sensor-2", "score": 65},
            {"name": "sensor-3", "score": 78},
        ]
        result = wyebot_health_threshold(data, min_score=80)
        assert len(result) == 2

    def test_threshold_empty_list(self):
        """Empty list returns empty list."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import (
            wyebot_health_threshold,
        )

        assert wyebot_health_threshold([]) == []

    def test_threshold_not_list_raises(self):
        """Non-list input raises AnsibleFilterError."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import (
            wyebot_health_threshold,
        )

        with pytest.raises(AnsibleFilterError, match="expects a list"):
            wyebot_health_threshold("not-a-list")

    def test_threshold_missing_score_key_raises(self):
        """Dict without 'score' key raises AnsibleFilterError."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import (
            wyebot_health_threshold,
        )

        with pytest.raises(AnsibleFilterError, match="'score' key"):
            wyebot_health_threshold([{"name": "sensor-1"}])

    def test_filter_module_exposes_all_filters(self):
        """FilterModule.filters() exposes all three health filters."""
        from ansible_collections.wyebot.wifi.plugins.filter.wyebot_health import FilterModule

        fm = FilterModule()
        filters = fm.filters()
        assert "wyebot_health_level" in filters
        assert "wyebot_health_color" in filters
        assert "wyebot_health_threshold" in filters
