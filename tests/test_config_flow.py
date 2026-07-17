"""Tests for JD Smart config flow helpers."""

from __future__ import annotations

import json
import unittest

from bootstrap import install_optional_ha_stubs

install_optional_ha_stubs()

from custom_components.jd_smart.config_flow import (  # noqa: E402
    _clean_input,
    _parse_capture_json,
    _same_account,
)


class CaptureImportTests(unittest.TestCase):
    """Test capture JSON normalization."""

    def test_normalized_capture_derives_pin_from_cookie(self) -> None:
        """The helper output can omit a duplicate PIN field."""
        data = _parse_capture_json(
            json.dumps(
                {
                    "cookie": "pin=test%20user; wskey=test-token",
                    "tgt": "test-token",
                    "device_id": "test-device",
                    "platform": "Android",
                    "app_version": "2.3.0",
                    "device_model": "Test Phone",
                    "platform_version": "16",
                    "channel": "test",
                    "user_agent": "test-agent",
                }
            )
        )

        self.assertEqual(data["pin"], "test user")
        self.assertEqual(data["platform"], "Android")
        self.assertEqual(data["device_model"], "Test Phone")

    def test_raw_capture_aliases_are_normalized(self) -> None:
        """Raw request names are accepted for manual tooling."""
        data = _parse_capture_json(
            json.dumps(
                {
                    "cookie": "pin=test; wskey=test-token",
                    "tgt": "test-token",
                    "plat": "Android",
                    "hard_platform": "Test Phone",
                    "plat_version": "16",
                    "User-Agent": "test-agent",
                }
            )
        )

        self.assertEqual(data["platform"], "Android")
        self.assertEqual(data["device_model"], "Test Phone")
        self.assertEqual(data["platform_version"], "16")
        self.assertEqual(data["user_agent"], "test-agent")

    def test_missing_credentials_are_rejected(self) -> None:
        """Both cookie and TGT are required."""
        with self.assertRaises(ValueError):
            _parse_capture_json(json.dumps({"tgt": "test-token"}))

    def test_empty_device_id_generates_unique_request_identity(self) -> None:
        """Manual setup must not reuse a published device identifier."""
        first = _clean_input({"cookie": "pin=test; wskey=token", "tgt": "token"})
        second = _clean_input({"cookie": "pin=test; wskey=token", "tgt": "token"})

        self.assertRegex(first["device_id"], r"^\d{20}$")
        self.assertNotEqual(first["device_id"], second["device_id"])

    def test_different_accounts_are_not_merged(self) -> None:
        """Importing another account must not overwrite configured credentials."""
        self.assertFalse(
            _same_account(
                {"cookie": "pin=first; wskey=token"},
                {"cookie": "pin=second; wskey=token"},
            )
        )


if __name__ == "__main__":
    unittest.main()
