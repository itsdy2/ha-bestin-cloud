"""Cloud action buttons; request success does not represent physical state."""
from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_UUID
from homeassistant.exceptions import HomeAssistantError

from .cloud import CloudError
from .const import DOMAIN
from .hub import BestinHub


async def async_setup_entry(hass, entry, async_add_entities):
    if CONF_UUID not in entry.data:
        return
    hub = BestinHub.get_hub(hass, entry)
    supported = getattr(hub.api, "user_elevator_supported", None)
    buttons = []
    if supported is not False:
        buttons.extend(ElevatorButton(hub, direction, supported) for direction in ("up", "down"))
    buttons.extend(LobbyDoorButton(hub, door) for door in getattr(hub.api, "lobby_doors", []))
    async_add_entities(buttons)


class LobbyDoorButton(ButtonEntity):
    """Open one discovered lobby door without claiming a lock state."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_translation_key = "lobby_door"
    _attr_icon = "mdi:door-open"

    def __init__(self, hub, door):
        self.hub = hub
        self.door_id = door["id"]
        self._attr_unique_id = f"{hub.hub_id}_lobby_door_{self.door_id}"
        self._attr_translation_placeholders = {"door": door["lobby_name"]}
        self._attr_device_info = {"identifiers": {(DOMAIN, str(hub.hub_id))}}

    @property
    def available(self):
        return self.hub.available

    async def async_press(self):
        try:
            await self.hub.api.request_open_door(self.door_id)
        except CloudError as exc:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="cloud_door_failed") from exc


class ElevatorButton(ButtonEntity):
    """Call an elevator in one direction, without a manually entered wallpad IP."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hub, direction, supported):
        self.hub = hub
        self.direction = direction
        self._attr_unique_id = f"{hub.hub_id}_elevator_call_{direction}"
        self._attr_translation_key = f"elevator_{direction}"
        self._attr_icon = f"mdi:elevator-{'up' if direction == 'up' else 'down'}"
        self._attr_entity_registry_enabled_default = supported is True
        self._attr_device_info = {"identifiers": {(DOMAIN, str(hub.hub_id))}}

    @property
    def available(self):
        return self.hub.available

    async def async_press(self):
        try:
            await self.hub.api.request_user_elevator(self.direction)
        except CloudError as exc:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="cloud_call_failed") from exc
