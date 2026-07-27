# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
    name: wyebot_health
    author:
      - Steve Fulmer (@stevefulmer)
    version_added: "1.0.0"
    short_description: Wyebot health score filters
    description:
      - Filter plugins for classifying and filtering Wyebot health scores.
      - C(wyebot_health_level) converts a numeric score (0-100) to a severity string.
      - C(wyebot_health_color) converts a numeric score to a dashboard color code.
      - C(wyebot_health_threshold) filters a list of health dicts, returning those below a threshold.
"""

EXAMPLES = """
# Convert a health score to a severity level
- name: Get health severity
  ansible.builtin.debug:
    msg: "{{ 45 | wyebot.wifi.wyebot_health_level }}"
    # Result: "warning"

# Get a dashboard color for a health score
- name: Get health color
  ansible.builtin.debug:
    msg: "{{ 95 | wyebot.wifi.wyebot_health_color }}"
    # Result: "green"

# Filter health data to find items below threshold
- name: Find unhealthy sensors
  ansible.builtin.debug:
    msg: "{{ health_data | wyebot.wifi.wyebot_health_threshold(min_score=80) }}"
  vars:
    health_data:
      - name: "sensor-1"
        score: 92
      - name: "sensor-2"
        score: 65
      - name: "sensor-3"
        score: 78

# Use in conditional logic
- name: Alert on critical health
  ansible.builtin.debug:
    msg: "CRITICAL: Sensor health is {{ sensor_score }}"
  when: (sensor_score | wyebot.wifi.wyebot_health_level) == 'critical'
"""

from ansible.errors import AnsibleFilterError


def wyebot_health_level(score):
    """Convert a numeric health score (0-100) to a severity level string.

    Args:
        score: Numeric health score between 0 and 100.

    Returns:
        str: One of 'critical', 'warning', 'good', or 'excellent'.

    Raises:
        AnsibleFilterError: If the score is not a valid number.
    """
    try:
        score = float(score)
    except (TypeError, ValueError):
        raise AnsibleFilterError(
            "wyebot_health_level requires a numeric score, got: {0}".format(type(score).__name__)
        )

    if score < 40:
        return "critical"
    elif score < 70:
        return "warning"
    elif score < 90:
        return "good"
    else:
        return "excellent"


def wyebot_health_color(score):
    """Convert a numeric health score (0-100) to a dashboard color code.

    Args:
        score: Numeric health score between 0 and 100.

    Returns:
        str: One of 'red', 'yellow', or 'green'.

    Raises:
        AnsibleFilterError: If the score is not a valid number.
    """
    try:
        score = float(score)
    except (TypeError, ValueError):
        raise AnsibleFilterError(
            "wyebot_health_color requires a numeric score, got: {0}".format(type(score).__name__)
        )

    if score < 40:
        return "red"
    elif score < 70:
        return "yellow"
    else:
        return "green"


def wyebot_health_threshold(data, min_score=70):
    """Filter a list of health dicts, returning only those below the threshold.

    Each dict in the list must have a 'score' key with a numeric value.

    Args:
        data: List of dicts, each containing a 'score' key.
        min_score: Minimum acceptable score (default 70). Items with scores
                   below this value are returned.

    Returns:
        list: Filtered list containing only dicts with scores below min_score.

    Raises:
        AnsibleFilterError: If data is not a list or items lack a score key.
    """
    if not isinstance(data, list):
        raise AnsibleFilterError(
            "wyebot_health_threshold expects a list, got: {0}".format(type(data).__name__)
        )

    try:
        min_score = float(min_score)
    except (TypeError, ValueError):
        raise AnsibleFilterError(
            "wyebot_health_threshold min_score must be numeric, got: {0}".format(
                type(min_score).__name__
            )
        )

    results = []
    for item in data:
        if not isinstance(item, dict):
            raise AnsibleFilterError(
                "wyebot_health_threshold expects a list of dicts, got item of type: {0}".format(
                    type(item).__name__
                )
            )
        if "score" not in item:
            raise AnsibleFilterError(
                "wyebot_health_threshold expects each dict to have a 'score' key"
            )
        try:
            item_score = float(item["score"])
        except (TypeError, ValueError):
            raise AnsibleFilterError(
                "wyebot_health_threshold score must be numeric, got: {0}".format(
                    type(item["score"]).__name__
                )
            )
        if item_score < min_score:
            results.append(item)

    return results


class FilterModule(object):
    """Wyebot health score filter plugins."""

    def filters(self):
        """Map filter names to their functions.

        Returns:
            dict: Filter name to function mapping.
        """
        return {
            "wyebot_health_level": wyebot_health_level,
            "wyebot_health_color": wyebot_health_color,
            "wyebot_health_threshold": wyebot_health_threshold,
        }
