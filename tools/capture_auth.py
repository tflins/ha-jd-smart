"""Capture JD Smart authentication fields with mitmproxy."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import unquote

from mitmproxy import ctx, http

API_HOST = "api.smart.jd.com"
COOKIE_HOST = "api.m.jd.com"


class JdSmartAuthCapture:
    """Collect the minimum fields required by the integration."""

    def __init__(self) -> None:
        self.cookie = ""
        self.auth_request: dict[str, str] | None = None
        self.completed = False

    def request(self, flow: http.HTTPFlow) -> None:
        """Inspect a request without persisting the full flow."""
        request = flow.request
        if request.pretty_host == COOKIE_HOST:
            cookie = request.headers.get("cookie", "")
            if _usable_cookie(cookie):
                self.cookie = cookie
                self._write_if_complete()
            return

        if request.pretty_host != API_HOST or not request.headers.get("tgt"):
            return

        query = request.query
        self.auth_request = {
            "cookie": request.headers.get("cookie", ""),
            "tgt": request.headers.get("tgt", ""),
            "pin": "",
            "sgm_context": request.headers.get("Sgm-Context", ""),
            "device_id": query.get("device_id", ""),
            "platform": query.get("plat", ""),
            "app_version": query.get("app_version", ""),
            "device_model": query.get("hard_platform", ""),
            "platform_version": query.get("plat_version", ""),
            "channel": query.get("channel", ""),
            "user_agent": request.headers.get("user-agent", ""),
        }
        self._write_if_complete()

    def _write_if_complete(self) -> None:
        if self.completed or self.auth_request is None:
            return

        data = dict(self.auth_request)
        data["cookie"] = data["cookie"] or self.cookie
        if not data["tgt"] or not _usable_cookie(data["cookie"]):
            return

        data["pin"] = _cookie_pin(data["cookie"])
        output = Path(
            os.environ.get("JD_SMART_AUTH_OUTPUT", "jd-smart-auth.json")
        ).expanduser()
        _write_private_json(output, data)
        self.completed = True
        ctx.log.info(f"JD Smart authentication saved to {output}")
        ctx.master.shutdown()


def _usable_cookie(cookie: str) -> bool:
    """Return whether the cookie contains the JD account identity."""
    lowered = cookie.lower()
    return "wskey=" in lowered and any(
        key in lowered for key in ("pin=", "pt_pin=", "pwdt_id=")
    )


def _cookie_pin(cookie: str) -> str:
    """Extract the decoded account PIN from a Cookie header."""
    values: dict[str, str] = {}
    for item in cookie.split(";"):
        key, separator, value = item.partition("=")
        if separator:
            values[key.strip().lower()] = unquote(value.strip())
    return next(
        (
            values[key]
            for key in ("pin", "pt_pin", "pwdt_id")
            if values.get(key)
        ),
        "",
    )


def _write_private_json(path: Path, data: dict[str, str]) -> None:
    """Atomically write authentication data with owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
        path.chmod(0o600)
    finally:
        if temporary.exists():
            temporary.unlink()


addons = [JdSmartAuthCapture()]
