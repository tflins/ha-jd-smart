"""Tests for the JD Smart API helpers."""

from __future__ import annotations

import base64
import asyncio
import json
import unittest
from unittest.mock import AsyncMock

from bootstrap import install_optional_ha_stubs

install_optional_ha_stubs()

from custom_components.jd_smart.api import (  # noqa: E402
    JdSmartCannotConnectError,
    JdSmartClient,
    JdSmartCredentials,
    JdSmartDeviceProfile,
    JdSmartSnapshot,
    JdSmartTokenRefreshAuthError,
    JdSmartTokenRefreshCannotConnectError,
    _build_cookie_from_tgt,
    _parse_refresh_a2_response,
    _tlv_app_info,
)


class _Response:
    """Minimal aiohttp response context manager."""

    def __init__(self, status: int) -> None:
        self.status = status

    async def __aenter__(self) -> _Response:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def text(self) -> str:
        return ""


class _Session:
    """Minimal session returning one HTTP status."""

    def __init__(self, status: int) -> None:
        self.status = status

    def post(self, *_args: object, **_kwargs: object) -> _Response:
        return _Response(self.status)


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
        packet = bytes(31) + (10).to_bytes(2, "big") + len(a2).to_bytes(2, "big") + a2

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

    def test_invalid_snapshot_stream_is_rejected(self) -> None:
        """Malformed cloud data must not replace a valid device snapshot."""
        with self.assertRaises(JdSmartCannotConnectError):
            JdSmartSnapshot.from_result({"streams": [{"current_value": "1"}]})


class JdSmartClientTests(unittest.IsolatedAsyncioTestCase):
    """Test stateful client behavior."""

    def setUp(self) -> None:
        """Create a client with a mocked shared HTTP session."""
        self.client = JdSmartClient(
            AsyncMock(),
            JdSmartCredentials(cookie="pin=test; wskey=old", tgt="old", pin="test"),
            JdSmartDeviceProfile(device_id="test-device"),
        )

    async def test_empty_control_streams_request_a_refresh(self) -> None:
        """An empty control snapshot must not clear coordinator state."""
        self.client._request_wangyin_json = AsyncMock(  # noqa: SLF001
            return_value={"result": json.dumps({"control_ret": "done", "streams": []})}
        )

        snapshot = await self.client.async_control_streams("feed", {"Power": 1})

        self.assertIsNone(snapshot)

    async def test_refresh_is_shared_between_coordinators(self) -> None:
        """Concurrent failures using one stale token refresh only once."""

        async def refresh() -> tuple[str, str]:
            await asyncio.sleep(0)
            self.client.credentials.tgt = "new"
            self.client.credentials.cookie = "pin=test; wskey=new"
            return "new", "pin=test; wskey=new"

        self.client._async_refresh_token = AsyncMock(side_effect=refresh)  # noqa: SLF001

        results = await asyncio.gather(
            self.client.async_refresh_token("old"),
            self.client.async_refresh_token("old"),
        )

        self.assertEqual(results, [("new", "pin=test; wskey=new")] * 2)
        self.client._async_refresh_token.assert_awaited_once()  # noqa: SLF001

    async def test_refresh_server_failure_is_transient(self) -> None:
        """A WJLogin server failure must not force account reauthentication."""
        client = JdSmartClient(
            _Session(500),
            self.client.credentials,
            self.client.profile,
        )

        with self.assertRaises(JdSmartTokenRefreshCannotConnectError):
            await client.async_refresh_token()

    async def test_refresh_rejected_credentials_require_reauth(self) -> None:
        """An explicit WJLogin rejection is classified as an auth failure."""
        client = JdSmartClient(
            _Session(401),
            self.client.credentials,
            self.client.profile,
        )

        with self.assertRaises(JdSmartTokenRefreshAuthError):
            await client.async_refresh_token()


if __name__ == "__main__":
    unittest.main()
