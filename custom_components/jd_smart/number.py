"""Number platform for JD Smart."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JdSmartConfigEntry
from .entity import JdSmartEntity

STREAM_ID = "ReserveTimeSetHour"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JdSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up JD Smart numbers."""
    async_add_entities(
        JdSmartReserveHours(coordinator)
        for coordinator in entry.runtime_data.coordinators.values()
        if STREAM_ID in coordinator.data.streams
    )


class JdSmartReserveHours(JdSmartEntity, NumberEntity):
    """JD Smart washer delay start hours."""

    _attr_translation_key = "washer_reserve_hours"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = 0
    _attr_native_max_value = 24
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    def __init__(self, coordinator) -> None:
        """Initialize number entity."""
        super().__init__(coordinator, "washer_reserve_hours")

    @property
    def native_value(self) -> float | None:
        """Return configured delay start hours."""
        value = self.streams.get(STREAM_ID)
        if value in (None, ""):
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @property
    def available(self) -> bool:
        """Return whether delay start can currently be configured."""
        return super().available and self.streams.get("Power") == "1"

    async def async_set_native_value(self, value: float) -> None:
        """Set delay start hours."""
        try:
            await self.coordinator.async_control_streams({STREAM_ID: int(value)})
        except Exception as err:
            raise HomeAssistantError("Unable to control JD Smart") from err
