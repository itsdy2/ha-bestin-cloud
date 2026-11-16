"""Button exposure and invocation with a minimal HA adapter."""
import types
import unittest
from test_cloud import cloud
from test_cloud_flow import load_without_ha


class HAError(Exception):
    def __init__(self, **kwargs):
        self.kwargs = kwargs


ns = load_without_ha("button.py", {"ButtonEntity": object, "CONF_UUID": "uuid", "DOMAIN": "bestin",
    "CloudError": cloud.CloudError, "HomeAssistantError": HAError,
    "BestinHub": types.SimpleNamespace(get_hub=lambda hass, entry: hass)})


class ButtonTests(unittest.IsolatedAsyncioTestCase):
    async def test_doors_exist_even_without_elevator(self):
        calls = []
        async def request(door_id):
            calls.append(door_id)
            if door_id == "2":
                raise cloud.CloudError("request_failed")
        hub = types.SimpleNamespace(api=types.SimpleNamespace(user_elevator_supported=False,
            lobby_doors=[{"id": "1", "lobby_name": "정문"}, {"id": "2", "lobby_name": "후문"}],
            request_open_door=request), hub_id="device", available=True)
        buttons = []
        await ns["async_setup_entry"](hub, types.SimpleNamespace(data={"uuid": "u"}), buttons.extend)
        self.assertEqual(len(buttons), 2)
        self.assertNotEqual(buttons[0]._attr_unique_id, buttons[1]._attr_unique_id)
        self.assertEqual(buttons[0]._attr_translation_placeholders, {"door": "정문"})
        await buttons[0].async_press()
        with self.assertRaises(HAError) as error:
            await buttons[1].async_press()
        self.assertEqual(error.exception.kwargs["translation_key"], "cloud_door_failed")
        self.assertEqual(calls, ["1", "2"])
        hub.available = False
        self.assertFalse(buttons[0].available)

    async def test_support_unknown_disabled_unsupported_absent(self):
        for support, count, enabled in ((True, 2, True), (None, 2, False), (False, 0, False)):
            hub = types.SimpleNamespace(api=types.SimpleNamespace(user_elevator_supported=support),
                                        hub_id="device", available=True)
            buttons = []
            await ns["async_setup_entry"](hub, types.SimpleNamespace(data={"uuid": "device"}), buttons.extend)
            self.assertEqual(len(buttons), count)
            for button in buttons:
                self.assertIs(button._attr_entity_registry_enabled_default, enabled)
        buttons = []
        await ns["async_setup_entry"](None, types.SimpleNamespace(data={}), buttons.extend)
        self.assertEqual(buttons, [])

    async def test_up_down_and_errors_no_retries(self):
        calls = []
        async def request(direction):
            calls.append(direction)
            if direction == "down":
                raise cloud.CloudError("auth_failed")
        hub = types.SimpleNamespace(api=types.SimpleNamespace(request_user_elevator=request),
                                    hub_id="device", available=True)
        await ns["ElevatorButton"](hub, "up", True).async_press()
        with self.assertRaises(HAError):
            await ns["ElevatorButton"](hub, "down", True).async_press()
        self.assertEqual(calls, ["up", "down"])


if __name__ == "__main__":
    unittest.main()
