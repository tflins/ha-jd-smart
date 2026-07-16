"""Button platform for JD Smart."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import JdSmartConfigEntry
from .entity import JdSmartEntity


@dataclass(frozen=True, kw_only=True)
class JdSmartButtonDescription(ButtonEntityDescription):
    """JD Smart button description."""

    stream_id: str
    command_value: int


BUTTONS: tuple[JdSmartButtonDescription, ...] = (
    JdSmartButtonDescription(
        key="washer_start",
        stream_id="Work",
        translation_key="washer_start",
        icon="mdi:play",
        command_value=1,
    ),
    JdSmartButtonDescription(
        key="washer_pause",
        stream_id="Work",
        translation_key="washer_pause",
        icon="mdi:pause",
        command_value=0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JdSmartConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up JD Smart buttons."""
    async_add_entities(
        JdSmartButton(coordinator, description)
        for coordinator in entry.runtime_data.coordinators.values()
        for description in BUTTONS
        if description.stream_id in coordinator.data.streams
    )


class JdSmartButton(JdSmartEntity, ButtonEntity):
    """JD Smart command button."""

    entity_description: JdSmartButtonDescription

    def __init__(
        self,
        coordinator,
        description: JdSmartButtonDescription,
    ) -> None:
        """Initialize button."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key

    @property
    def available(self) -> bool:
        """Return whether the command is valid for the current state."""
        if not super().available or self.streams.get("Power") != "1":
            return False
        state = self.streams.get("State")
        if self.entity_description.command_value == 1:
            return state in {"0", "14"}
        return state in {"1", "4", "5", "6"}

    async def async_press(self) -> None:
        """Send the command."""
        try:
            await self.coordinator.async_control_streams(
                {
                    self.entity_description.stream_id: (
                        self.entity_description.command_value
                    )
                }
            )
        except Exception as err:
            raise HomeAssistantError("Unable to control JD Smart") from err
