"""Tests for the JD Smart capture helper."""

from __future__ import annotations

import json
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest

mitmproxy = types.ModuleType("mitmproxy")
mitmproxy.ctx = types.SimpleNamespace()
mitmproxy.http = types.SimpleNamespace(HTTPFlow=object)
sys.modules.setdefault("mitmproxy", mitmproxy)

from tools.capture_auth import (  # noqa: E402
    _cookie_pin,
    _usable_cookie,
    _write_private_json,
)


class CaptureHelperTests(unittest.TestCase):
    """Test capture helper security and normalization."""

    def test_cookie_identity_is_detected(self) -> None:
        """Only cookies with both account and WJLogin values are accepted."""
        self.assertTrue(_usable_cookie("pin=test; wskey=token"))
        self.assertFalse(_usable_cookie("pin=test"))
        self.assertFalse(_usable_cookie("wskey=token"))

    def test_cookie_pin_is_decoded(self) -> None:
        """URL-encoded account identifiers are normalized."""
        self.assertEqual(_cookie_pin("pin=test%20user; wskey=token"), "test user")

    def test_auth_file_is_owner_only(self) -> None:
        """Authentication files are never world-readable."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "auth.json"

            _write_private_json(path, {"cookie": "secret", "tgt": "secret"})

            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(
                json.loads(path.read_text()),
                {
                    "cookie": "secret",
                    "tgt": "secret",
                },
            )


if __name__ == "__main__":
    unittest.main()
