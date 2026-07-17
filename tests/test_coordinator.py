"""Tests for the JD Smart coordinator state handling."""

from __future__ import annotations

import unittest

from bootstrap import install_optional_ha_stubs

install_optional_ha_stubs()

from custom_components.jd_smart.api import (  # noqa: E402
    JdSmartCannotConnectError,
    JdSmartSnapshot,
)
from custom_components.jd_smart.coordinator import JdSmartCoordinator  # noqa: E402


def _snapshot(
    *,
    digest: str = "digest",
    status: str = "1",
    streams: dict[str, str] | None = None,
) -> JdSmartSnapshot:
    """Build a snapshot for coordinator tests."""
    return JdSmartSnapshot(
        digest=digest,
        status=status,
        from_device_success=True,
        streams=streams if streams is not None else {"Power": "1"},
    )


def _coordinator(data: JdSmartSnapshot | None = None) -> JdSmartCoordinator:
    """Build a coordinator without starting Home Assistant scheduling."""
    coordinator = object.__new__(JdSmartCoordinator)
    coordinator.data = data
    coordinator._consecutive_update_failures = 0  # noqa: SLF001
    coordinator._last_successful_update = None  # noqa: SLF001
    return coordinator


class CoordinatorSnapshotTests(unittest.TestCase):
    """Test snapshot validation and merging."""

    def test_offline_snapshot_is_rejected(self) -> None:
        """An offline response must not reset the failure grace period."""
        coordinator = _coordinator(_snapshot())

        with self.assertRaises(JdSmartCannotConnectError):
            coordinator._validate_snapshot(_snapshot(status="0"))  # noqa: SLF001

    def test_unchanged_empty_snapshot_keeps_current_data(self) -> None:
        """A digest-only response keeps the last full snapshot."""
        current = _snapshot()
        coordinator = _coordinator(current)

        result = coordinator._validate_snapshot(  # noqa: SLF001
            _snapshot(streams={})
        )

        self.assertIs(result, current)

    def test_partial_control_snapshot_is_merged(self) -> None:
        """Control responses update only streams returned by the cloud."""
        coordinator = _coordinator(_snapshot(streams={"Power": "0", "Mode": "2"}))

        result = coordinator._merge_control_snapshot(  # noqa: SLF001
            _snapshot(digest="new", streams={"Power": "1"})
        )

        self.assertEqual(result.streams, {"Power": "1", "Mode": "2"})
        self.assertEqual(result.digest, "new")
