"""Sensor platform for JD Smart."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JdSmartConfigEntry
from .entity import JdSmartEntity


@dataclass(frozen=True, kw_only=True)
class JdSmartSensorDescription(SensorEntityDescription):
    """JD Smart sensor description."""

    stream_id: str
    value_map: dict[str, str] | None = None


SENSORS: tuple[JdSmartSensorDescription, ...] = (
    JdSmartSensorDescription(
        key="curtemp",
        stream_id="curtemp",
        translation_key="current_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JdSmartSensorDescription(
        key="curhum",
        stream_id="curhum",
        translation_key="current_humidity",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JdSmartSensorDescription(
        key="tvoc",
        stream_id="tvoc",
        translation_key="tvoc",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JdSmartSensorDescription(
        key="time_sum",
        stream_id="time_sum",
        translation_key="runtime_total",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JdSmartSensorDescription(
        key="time_clr",
        stream_id="time_clr",
        translation_key="clean_runtime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JdSmartSensorDescription(
        key="speaker",
        stream_id="speaker",
        translation_key="speaker_raw",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JdSmartSensorDescription(
        key="mdpmode",
        stream_id="mdpmode",
        translation_key="mdp_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JdSmartSensorDescription(
        key="ptcheat",
        stream_id="ptcheat",
        translation_key="protection_state",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JdSmartSensorDescription(
        key="washer_state",
        stream_id="State",
        translation_key="washer_state",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "standby",
            "reserved",
            "washing",
            "rinsing",
            "spinning",
            "complete",
            "paused",
        ],
        value_map={
            "0": "standby",
            "1": "reserved",
            "4": "washing",
            "5": "rinsing",
            "6": "spinning",
            "7": "complete",
            "14": "paused",
        },
    ),
    JdSmartSensorDescription(
        key="washer_remaining_time",
        stream_id="RemainingTimeMin",
        translation_key="washer_remaining_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JdSmartSensorDescription(
        key="washer_reserve_remaining",
        stream_id="ReserveTimeRemainingMinute",
        translation_key="washer_reserve_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JdSmartSensorDescription(
        key="washer_error_code",
        stream_id="Error",
        translation_key="washer_error_code",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JdSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up JD Smart sensors."""
    async_add_entities(
        JdSmartSensor(coordinator, description)
        for coordinator in entry.runtime_data.coordinators.values()
        for description in SENSORS
        if description.stream_id in coordinator.data.streams
    )


class JdSmartSensor(JdSmartEntity, SensorEntity):
    """JD Smart stream sensor."""

    entity_description: JdSmartSensorDescription

    def __init__(
        self,
        coordinator,
        description: JdSmartSensorDescription,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key

    @property
    def native_value(self) -> str | float | None:
        """Return sensor value."""
        value = self.streams.get(self.entity_description.stream_id)
        if value == "":
            return None
        if self.entity_description.value_map is not None:
            return self.entity_description.value_map.get(value)
        if self.entity_description.state_class is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
        return value
