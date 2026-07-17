"""Coordinator for the JD Smart integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.components import persistent_notification
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .api import (
    JdSmartAuthError,
    JdSmartCannotConnectError,
    JdSmartClient,
    JdSmartError,
    JdSmartSnapshot,
    JdSmartTokenRefreshAuthError,
    JdSmartTokenRefreshCannotConnectError,
    JdSmartTokenRefreshError,
)
from .const import (
    CONF_COOKIE,
    CONF_TGT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    FAST_POLL_DURATION,
    FAST_POLL_INTERVAL,
    LOGGER,
    UPDATE_FAILURE_GRACE_PERIOD,
)

type JdSmartConfigEntry = ConfigEntry[JdSmartRuntimeData]


@dataclass
class JdSmartRuntimeData:
    """Runtime data for JD Smart."""

    client: JdSmartClient
    coordinators: dict[str, JdSmartCoordinator]


class JdSmartCoordinator(DataUpdateCoordinator[JdSmartSnapshot]):
    """Data coordinator for JD Smart."""

    config_entry: JdSmartConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: JdSmartConfigEntry,
        client: JdSmartClient,
        feed_id: str,
        device_name: str | None,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.feed_id = feed_id
        self.device_name = device_name
        self._fast_poll_cancel: Callable[[], None] | None = None
        self._consecutive_update_failures = 0
        self._last_successful_update: datetime | None = None

    async def _async_update_data(self) -> JdSmartSnapshot:
        """Fetch latest snapshot."""
        digest = self.data.digest if self.data else ""
        stale_tgt = self.client.credentials.tgt
        try:
            snapshot = await self.client.async_get_snapshot(self.feed_id, digest)
            return self._handle_update_success(self._validate_snapshot(snapshot))
        except JdSmartAuthError:
            LOGGER.info("JD Smart snapshot authentication failed; refreshing token")
            return await self._async_refresh_and_retry(digest, stale_tgt)
        except JdSmartCannotConnectError as err:
            if self.data is None:
                raise ConfigEntryNotReady from err
            return self._handle_update_failure(err)
        except JdSmartError as err:
            return self._handle_update_failure(err)

    async def _async_refresh_and_retry(
        self, digest: str, stale_tgt: str
    ) -> JdSmartSnapshot:
        """Refresh expired credentials and retry the snapshot once."""
        try:
            await self._async_refresh_token(stale_tgt)
        except JdSmartTokenRefreshCannotConnectError as err:
            if self.data is None:
                raise ConfigEntryNotReady from err
            return self._handle_update_failure(err)
        except JdSmartTokenRefreshAuthError as err:
            self._async_create_reauth_notification()
            raise ConfigEntryAuthFailed from err
        except JdSmartTokenRefreshError as err:
            self._async_create_token_refresh_failed_notification(err)
            return self._handle_update_failure(err)

        try:
            snapshot = await self.client.async_get_snapshot(self.feed_id, digest)
            return self._handle_update_success(self._validate_snapshot(snapshot))
        except JdSmartAuthError as err:
            self._async_create_reauth_notification()
            raise ConfigEntryAuthFailed from err
        except JdSmartCannotConnectError as err:
            if self.data is None:
                raise ConfigEntryNotReady from err
            return self._handle_update_failure(err)
        except JdSmartError as err:
            return self._handle_update_failure(err)

    async def async_control_streams(self, commands: dict[str, object]) -> None:
        """Control streams and refresh state."""
        stale_tgt = self.client.credentials.tgt
        try:
            snapshot = await self.client.async_control_streams(self.feed_id, commands)
        except JdSmartAuthError as err:
            LOGGER.warning(
                "JD Smart control authentication failed: "
                "feed_id=%s, commands=%s, error=%s",
                self.feed_id,
                commands,
                err,
            )
            try:
                await self._async_refresh_token(stale_tgt)
                snapshot = await self.client.async_control_streams(
                    self.feed_id,
                    commands,
                )
            except JdSmartTokenRefreshAuthError as refresh_err:
                self._async_create_reauth_notification()
                self.config_entry.async_start_reauth(self.hass)
                raise ConfigEntryAuthFailed from refresh_err
            except JdSmartAuthError as refresh_err:
                self._async_create_reauth_notification()
                self.config_entry.async_start_reauth(self.hass)
                raise ConfigEntryAuthFailed from refresh_err
            except JdSmartTokenRefreshCannotConnectError as refresh_err:
                raise UpdateFailed(
                    "Unable to refresh JD Smart authentication"
                ) from refresh_err
            except JdSmartTokenRefreshError as refresh_err:
                self._async_create_token_refresh_failed_notification(refresh_err)
                raise UpdateFailed(
                    "Unable to refresh JD Smart authentication"
                ) from refresh_err
            except JdSmartError as refresh_err:
                LOGGER.warning(
                    "JD Smart control failed after token refresh: "
                    "feed_id=%s, commands=%s, error=%s",
                    self.feed_id,
                    commands,
                    refresh_err,
                )
                raise UpdateFailed("Unable to control JD Smart") from refresh_err
        except JdSmartError as err:
            LOGGER.warning(
                "JD Smart control failed: feed_id=%s, commands=%s, error=%s",
                self.feed_id,
                commands,
                err,
            )
            raise UpdateFailed("Unable to control JD Smart") from err
        if snapshot is not None:
            snapshot = self._merge_control_snapshot(snapshot)
            snapshot = self._validate_snapshot(snapshot)
            self.async_set_updated_data(self._handle_update_success(snapshot))
        self.trigger_fast_polling()
        await self.async_request_refresh()

    async def _async_refresh_token(self, stale_tgt: str | None = None) -> None:
        """Refresh token and persist the refreshed values."""
        new_tgt, new_cookie = await self.client.async_refresh_token(stale_tgt)
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data={
                **self.config_entry.data,
                CONF_TGT: new_tgt,
                CONF_COOKIE: new_cookie,
            },
        )

    def _validate_snapshot(self, snapshot: JdSmartSnapshot) -> JdSmartSnapshot:
        """Validate device availability and preserve unchanged snapshots."""
        if snapshot.status == "0":
            raise JdSmartCannotConnectError("JD Smart device is offline")
        if snapshot.streams:
            return snapshot
        if self.data is not None and snapshot.digest in {"", self.data.digest}:
            return self.data
        raise JdSmartCannotConnectError("JD Smart snapshot did not include streams")

    def _merge_control_snapshot(self, snapshot: JdSmartSnapshot) -> JdSmartSnapshot:
        """Merge partial control responses into the latest full snapshot."""
        if self.data is None:
            return snapshot
        return JdSmartSnapshot(
            digest=snapshot.digest or self.data.digest,
            status=snapshot.status or self.data.status,
            from_device_success=snapshot.from_device_success,
            streams={**self.data.streams, **snapshot.streams},
        )

    def _handle_update_success(self, snapshot: JdSmartSnapshot) -> JdSmartSnapshot:
        """Record a successful update and return its snapshot."""
        self._consecutive_update_failures = 0
        self._last_successful_update = dt_util.utcnow()
        return snapshot

    def _handle_update_failure(self, err: JdSmartError) -> JdSmartSnapshot:
        """Keep recent data during transient failures before going unavailable."""
        self._consecutive_update_failures += 1
        now = dt_util.utcnow()
        if self.data is not None and self._last_successful_update is not None:
            stale_for = now - self._last_successful_update
            if stale_for < UPDATE_FAILURE_GRACE_PERIOD:
                LOGGER.debug(
                    "JD Smart update failed; retaining cached snapshot: "
                    "feed_id=%s, failures=%s, stale_for=%s, error_type=%s, error=%s",
                    self.feed_id,
                    self._consecutive_update_failures,
                    stale_for,
                    err.__class__.__name__,
                    err,
                )
                return self.data
        raise UpdateFailed(
            f"Unable to update JD Smart after {self._consecutive_update_failures} failures"
        ) from err

    @callback
    def _async_create_reauth_notification(self) -> None:
        """Create a persistent reauth notification."""
        persistent_notification.async_create(
            self.hass,
            (
                "JD Smart could not update the device data several times. "
                "Open Settings > Devices & services and reauthenticate JD Smart."
            ),
            title="JD Smart authentication required",
            notification_id=f"{DOMAIN}_{self.feed_id}_reauth",
        )

    @callback
    def _async_create_token_refresh_failed_notification(self, err: Exception) -> None:
        """Create a persistent notification for token refresh failures."""
        reason = str(err) or err.__class__.__name__
        persistent_notification.async_create(
            self.hass,
            (
                "JD Smart failed to refresh authentication. "
                f"Device: {self.device_name or self.feed_id}. "
                f"Reason: {reason}. "
                "Open Settings > Devices & services and update JD Smart authentication."
            ),
            title="JD Smart authentication refresh failed",
            notification_id=f"{DOMAIN}_{self.feed_id}_token_refresh_failed",
        )

    def async_shutdown(self) -> None:
        """Cancel pending coordinator callbacks."""
        if self._fast_poll_cancel:
            self._fast_poll_cancel()
            self._fast_poll_cancel = None

    @callback
    def trigger_fast_polling(self) -> None:
        """Temporarily poll faster after a control command."""
        self.update_interval = FAST_POLL_INTERVAL
        if self._fast_poll_cancel:
            self._fast_poll_cancel()
        end = dt_util.utcnow() + FAST_POLL_DURATION
        self._fast_poll_cancel = async_track_point_in_utc_time(
            self.hass, self._reset_polling, end
        )

    @callback
    def _reset_polling(self, _now: datetime) -> None:
        """Reset polling interval."""
        self.update_interval = DEFAULT_SCAN_INTERVAL
        self._fast_poll_cancel = None
