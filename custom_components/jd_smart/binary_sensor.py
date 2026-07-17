"""Binary sensor platform for JD Smart."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JdSmartConfigEntry
from .entity import JdSmartEntity


@dataclass(frozen=True, kw_only=True)
class JdSmartBinarySensorDescription(BinarySensorEntityDescription):
    """JD Smart binary sensor description."""

    stream_id: str
    active_values: frozenset[str]
    nonzero_is_active: bool = False


BINARY_SENSORS: tuple[JdSmartBinarySensorDescription, ...] = (
    JdSmartBinarySensorDescription(
        key="washer_running",
        stream_id="State",
        translation_key="washer_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        active_values=frozenset({"4", "5", "6"}),
    ),
    JdSmartBinarySensorDescription(
        key="washer_complete",
        stream_id="State",
        translation_key="washer_complete",
        active_values=frozenset({"7"}),
    ),
    JdSmartBinarySensorDescription(
        key="washer_problem",
        stream_id="Error",
        translation_key="washer_problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        active_values=frozenset(),
        nonzero_is_active=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JdSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up JD Smart binary sensors."""
    async_add_entities(
        JdSmartBinarySensor(coordinator, description)
        for coordinator in entry.runtime_data.coordinators.values()
        for description in BINARY_SENSORS
        if description.stream_id in coordinator.data.streams
    )


class JdSmartBinarySensor(JdSmartEntity, BinarySensorEntity):
    """JD Smart stream binary sensor."""

    entity_description: JdSmartBinarySensorDescription

    def __init__(
        self,
        coordinator,
        description: JdSmartBinarySensorDescription,
    ) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key

    @property
    def is_on(self) -> bool | None:
        """Return binary sensor state."""
        value = self.streams.get(self.entity_description.stream_id)
        if value in (None, ""):
            return None
        if self.entity_description.nonzero_is_active:
            return value != "0"
        return value in self.entity_description.active_values
