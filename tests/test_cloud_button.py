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
