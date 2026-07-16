"""Tests for the JD Smart API helpers."""

from __future__ import annotations

import base64
import unittest

from custom_components.jd_smart.api import (
    JdSmartDeviceProfile,
    _build_cookie_from_tgt,
    _parse_refresh_a2_response,
    _tlv_app_info,
)


class WJLoginTests(unittest.TestCase):
    """Test WJLogin packet helpers."""

    def test_app_info_uses_jd_smart_display_name(self) -> None:
        """The app name must match the Android client registration."""
        payload = _tlv_app_info(JdSmartDeviceProfile(device_id="test-device"))

        self.assertIn("京东小家".encode(), payload)
        self.assertNotIn(b"jdsmart", payload)

    def test_refresh_response_returns_url_safe_a2(self) -> None:
        """A successful response returns the refreshed A2 token."""
        a2 = b"refreshed-a2"
        packet = bytes(31) + (10).to_bytes(2, "big") + len(a2).to_bytes(
            2, "big"
        ) + a2

        token = _parse_refresh_a2_response(packet)

        self.assertEqual(
            token,
            base64.urlsafe_b64encode(a2).decode().rstrip("="),
        )

    def test_refreshed_cookie_updates_identity_fields(self) -> None:
        """Refreshed credentials replace stale cookie values."""
        cookie = "pin=old; pt_pin=old; wskey=old; other=value"

        refreshed = _build_cookie_from_tgt(cookie, "new-token", "new pin")

        self.assertIn("pin=new%20pin", refreshed)
        self.assertIn("pt_pin=new%20pin", refreshed)
        self.assertIn("pwdt_id=new%20pin", refreshed)
        self.assertIn("wskey=new-token", refreshed)
        self.assertIn("other=value", refreshed)


if __name__ == "__main__":
    unittest.main()
