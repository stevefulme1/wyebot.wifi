# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
    name: wyebot_alerts
    author:
      - Steve Fulmer (@stevefulmer)
    version_added: "1.0.0"
    short_description: Wyebot alert classification filters
    description:
      - Filter plugins for classifying and summarizing Wyebot alerts.
      - C(wyebot_alert_severity) filters alerts by severity level.
      - C(wyebot_alert_category) filters alerts by category.
      - C(wyebot_alert_unacknowledged) returns only unacknowledged alerts.
      - C(wyebot_alert_summary) returns a summary dict with counts by severity and category.
"""

EXAMPLES = """
# Filter alerts by severity
- name: Get critical alerts
  ansible.builtin.debug:
    msg: "{{ alerts | wyebot.wifi.wyebot_alert_severity('critical') }}"
  vars:
    alerts:
      - id: 1
        severity: critical
        category: connectivity
        acknowledged: false
        message: "Sensor offline"
      - id: 2
        severity: warning
        category: performance
        acknowledged: true
        message: "High latency detected"

# Filter alerts by category
- name: Get connectivity alerts
  ansible.builtin.debug:
    msg: "{{ alerts | wyebot.wifi.wyebot_alert_category('connectivity') }}"

# Get unacknowledged alerts only
- name: Get unacknowledged alerts
  ansible.builtin.debug:
    msg: "{{ alerts | wyebot.wifi.wyebot_alert_unacknowledged }}"

# Generate an alert summary
- name: Alert summary
  ansible.builtin.debug:
    msg: "{{ alerts | wyebot.wifi.wyebot_alert_summary }}"
    # Result:
    # {
    #   "total": 2,
    #   "by_severity": {"critical": 1, "warning": 1},
    #   "by_category": {"connectivity": 1, "performance": 1},
    #   "unacknowledged": 1
    # }

# Chain filters together
- name: Critical unacknowledged connectivity alerts
  ansible.builtin.debug:
    msg: >-
      {{ alerts
         | wyebot.wifi.wyebot_alert_severity('critical')
         | wyebot.wifi.wyebot_alert_category('connectivity')
         | wyebot.wifi.wyebot_alert_unacknowledged }}
"""

from ansible.errors import AnsibleFilterError


def wyebot_alert_severity(alerts, severity):
    """Filter a list of alert dicts by severity level.

    Args:
        alerts: List of alert dicts, each containing a 'severity' key.
        severity: Severity level string to filter by (e.g. 'critical', 'warning', 'info').

    Returns:
        list: Alerts matching the specified severity.

    Raises:
        AnsibleFilterError: If alerts is not a list or severity is not a string.
    """
    if not isinstance(alerts, list):
        raise AnsibleFilterError(
            "wyebot_alert_severity expects a list, got: {0}".format(type(alerts).__name__)
        )
    if not isinstance(severity, str):
        raise AnsibleFilterError(
            "wyebot_alert_severity severity must be a string, got: {0}".format(
                type(severity).__name__
            )
        )

    severity_lower = severity.lower()
    return [
        alert for alert in alerts
        if isinstance(alert, dict) and str(alert.get("severity", "")).lower() == severity_lower
    ]


def wyebot_alert_category(alerts, category):
    """Filter a list of alert dicts by category.

    Args:
        alerts: List of alert dicts, each containing a 'category' key.
        category: Category string to filter by (e.g. 'connectivity', 'performance', 'security').

    Returns:
        list: Alerts matching the specified category.

    Raises:
        AnsibleFilterError: If alerts is not a list or category is not a string.
    """
    if not isinstance(alerts, list):
        raise AnsibleFilterError(
            "wyebot_alert_category expects a list, got: {0}".format(type(alerts).__name__)
        )
    if not isinstance(category, str):
        raise AnsibleFilterError(
            "wyebot_alert_category category must be a string, got: {0}".format(
                type(category).__name__
            )
        )

    category_lower = category.lower()
    return [
        alert for alert in alerts
        if isinstance(alert, dict) and str(alert.get("category", "")).lower() == category_lower
    ]


def wyebot_alert_unacknowledged(alerts):
    """Filter a list of alert dicts to return only unacknowledged alerts.

    An alert is considered unacknowledged if its 'acknowledged' field is falsy
    or absent.

    Args:
        alerts: List of alert dicts.

    Returns:
        list: Alerts that have not been acknowledged.

    Raises:
        AnsibleFilterError: If alerts is not a list.
    """
    if not isinstance(alerts, list):
        raise AnsibleFilterError(
            "wyebot_alert_unacknowledged expects a list, got: {0}".format(type(alerts).__name__)
        )

    return [
        alert for alert in alerts
        if isinstance(alert, dict) and not alert.get("acknowledged", False)
    ]


def wyebot_alert_summary(alerts):
    """Generate a summary dict with counts by severity and category.

    Args:
        alerts: List of alert dicts.

    Returns:
        dict: Summary containing:
            - total (int): Total number of alerts.
            - by_severity (dict): Count of alerts per severity level.
            - by_category (dict): Count of alerts per category.
            - unacknowledged (int): Count of unacknowledged alerts.

    Raises:
        AnsibleFilterError: If alerts is not a list.
    """
    if not isinstance(alerts, list):
        raise AnsibleFilterError(
            "wyebot_alert_summary expects a list, got: {0}".format(type(alerts).__name__)
        )

    by_severity = {}
    by_category = {}
    unacknowledged = 0

    for alert in alerts:
        if not isinstance(alert, dict):
            continue

        severity = str(alert.get("severity", "unknown")).lower()
        by_severity[severity] = by_severity.get(severity, 0) + 1

        category = str(alert.get("category", "unknown")).lower()
        by_category[category] = by_category.get(category, 0) + 1

        if not alert.get("acknowledged", False):
            unacknowledged += 1

    return {
        "total": len(alerts),
        "by_severity": by_severity,
        "by_category": by_category,
        "unacknowledged": unacknowledged,
    }


class FilterModule(object):
    """Wyebot alert classification filter plugins."""

    def filters(self):
        """Map filter names to their functions.

        Returns:
            dict: Filter name to function mapping.
        """
        return {
            "wyebot_alert_severity": wyebot_alert_severity,
            "wyebot_alert_category": wyebot_alert_category,
            "wyebot_alert_unacknowledged": wyebot_alert_unacknowledged,
            "wyebot_alert_summary": wyebot_alert_summary,
        }
