"""Tests for JD Smart config flow helpers."""

from __future__ import annotations

import json
import unittest

from custom_components.jd_smart.config_flow import _parse_capture_json


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


if __name__ == "__main__":
    unittest.main()
