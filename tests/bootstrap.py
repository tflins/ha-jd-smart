"""Minimal stubs for optional Home Assistant runtime dependencies."""

from __future__ import annotations

import sys
import types


def install_optional_ha_stubs() -> None:
    """Stub HA features that are unrelated to this integration's tests."""
    hass_nabucasa = types.ModuleType("hass_nabucasa")
    hass_nabucasa.remote = types.ModuleType("hass_nabucasa.remote")
    sys.modules.setdefault("hass_nabucasa", hass_nabucasa)
    sys.modules.setdefault("hass_nabucasa.remote", hass_nabucasa.remote)
