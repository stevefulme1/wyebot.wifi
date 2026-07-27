# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Nox sessions for wyebot.wifi collection using ansible-nox."""

from __future__ import annotations

try:
    from ansible_nox import add_sessions

    add_sessions()
except ImportError:
    pass
