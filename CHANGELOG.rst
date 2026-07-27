===========================
wyebot.wifi Release Notes
===========================

.. contents:: Topics

v0.1.0
======

Release Summary
---------------

Initial release of the ``wyebot.wifi`` Ansible collection for Wyebot WiFi
monitoring platform integration. Provides modules, EDA event sources, and
roles for closed-loop WiFi automation.

New Modules
-----------

- ``wyebot.wifi.wyebot_locations`` - Query Wyebot locations.
- ``wyebot.wifi.wyebot_sensors`` - Query sensors at a location.
- ``wyebot.wifi.wyebot_sensor_info`` - Get detailed sensor information.
- ``wyebot.wifi.wyebot_network_tests`` - Retrieve network test results.
- ``wyebot.wifi.wyebot_alerts`` - Query alerts by location or sensor.
- ``wyebot.wifi.wyebot_clients`` - List connected WiFi clients.
- ``wyebot.wifi.wyebot_aps`` - List access points visible to a sensor.
- ``wyebot.wifi.wyebot_ssids`` - List SSIDs detected by a sensor.
- ``wyebot.wifi.wyebot_channels`` - Get channel utilization data.
- ``wyebot.wifi.wyebot_interference`` - Get RF interference data.
- ``wyebot.wifi.wyebot_rogue_aps`` - Detect rogue access points.
- ``wyebot.wifi.wyebot_spectrum`` - Get spectrum analysis data.
- ``wyebot.wifi.wyebot_health`` - Get sensor health metrics.
- ``wyebot.wifi.wyebot_firmware`` - Get sensor firmware information.
- ``wyebot.wifi.wyebot_api_key`` - Create or revoke API keys.

New Plugins
-----------

- ``wyebot.wifi.wyebot_alerts`` - EDA event source for Wyebot alerts (polling).
- ``wyebot.wifi.wyebot_webhook`` - EDA event source for Wyebot webhooks.
- ``wyebot.wifi.wyebot_kafka`` - EDA event source for Wyebot Kafka streams.

New Roles
---------

- ``wyebot.wifi.remediate_channel`` - Closed-loop channel remediation via vendor collections.
- ``wyebot.wifi.remediate_rogue`` - Rogue AP containment workflow.
