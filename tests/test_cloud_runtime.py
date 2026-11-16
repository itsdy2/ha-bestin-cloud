"""Real runtime refresh/start methods under deterministic HA adapters."""
import ast
from datetime import datetime
import logging
from pathlib import Path
import types
import unittest
from test_cloud import cloud

ROOT = Path(__file__).resolve().parents[1] / "custom_components/bestin"


class AuthFailed(Exception):
    pass


class NotReady(Exception):
    pass


def extract_method(filename, class_name, method, scope):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    cls = next(v for v in tree.body if isinstance(v, ast.ClassDef) and v.name == class_name)
    node = next(v for v in cls.body if isinstance(v, ast.AsyncFunctionDef) and v.name == method)
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, str(ROOT / filename), "exec"), scope)
    return scope[method]


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_capabilities_and_failures(self):
        from test_cloud import Session, Response
        scope = {"CloudAPI": cloud.CloudAPI, "CloudError": cloud.CloudError,
                 "CONF_SESSION": "session", "LOGGER": logging.getLogger("test"),
                 "elevator_support": cloud.elevator_support, "onepass_support": cloud.onepass_support}
        discover = extract_method("center.py", "CenterAPIv2", "discover_user_elevator", scope)
        for response, expected in ((Response({"additional": []}), 0),
                                   (Response({"additional": [{"category": "onepass"}]}), 1),
                                   (Response({}), 1), (Response({}, 500), 1)):
            calls = []
            async def doors():
                calls.append(True)
            owner = types.SimpleNamespace(session=Session(response), discover_doors=doors,
                entry=types.SimpleNamespace(data={"session": {
                    "url": "https://site.example", "access-token": "t"}}))
            await discover(owner)
            self.assertEqual(len(calls), expected)

    async def test_door_discovery_and_latest_session(self):
        from test_cloud import Session, Response
        scope = {"CloudAPI": cloud.CloudAPI, "CloudError": cloud.CloudError,
                 "CONF_SESSION": "session", "LOGGER": logging.getLogger("test")}
        discover = extract_method("center.py", "CenterAPIv2", "discover_doors", scope)
        request = extract_method("center.py", "CenterAPIv2", "request_open_door", scope)
        session = Session(Response([{"id": 1, "lobby_name": "정문"}]), Response({"result": "ok"}))
        owner = types.SimpleNamespace(session=session, lobby_doors=[], entry=types.SimpleNamespace(
            data={"session": {"url": "https://site.example", "access-token": "old", "alias": "HA"}}))
        await discover(owner)
        self.assertEqual(owner.lobby_doors, [{"id": "1", "lobby_name": "정문"}])
        owner.entry.data["session"]["access-token"] = "new"
        await request(owner, "1")
        self.assertEqual(session.calls[1][2]["headers"]["access-token"], "new")
        owner.session = Session(Response({}, 404))
        await discover(owner)
        self.assertEqual(owner.lobby_doors, [])
        with self.assertRaises(cloud.CloudError):
            await request(owner, "other")

    async def test_refresh_saves_session_without_mutating_uuid(self):
        updates = []
        class API:
            def __init__(self, session, uuid):
                self.uuid = uuid
            async def login(self):
                return {"url": "https://site.example", "access-token": "new"}
        scope = {"CloudAPI": API, "CloudError": cloud.CloudError, "datetime": datetime,
                 "CONF_UUID": "uuid", "CONF_SESSION": "session",
                 "ConfigEntryAuthFailed": AuthFailed, "ConfigEntryNotReady": NotReady}
        method = extract_method("center.py", "CenterAPIv2", "_v2_refresh_session", scope)
        entry = types.SimpleNamespace(data={"uuid": "same", "session": {"access-token": "old"}})
        owner = types.SimpleNamespace(session=None, entry=entry, hass=types.SimpleNamespace(
            config_entries=types.SimpleNamespace(async_update_entry=lambda e, **kw: updates.append(kw))))
        await method(owner)
        self.assertEqual(updates[0]["data"]["uuid"], "same")
        self.assertEqual(updates[0]["data"]["session"]["access-token"], "new")

    async def test_start_auth_and_network_errors_reach_ha(self):
        for code, expected in (("auth_failed", AuthFailed), ("network_error", NotReady)):
            class API:
                def __init__(self, *args):
                    pass
                async def login(self):
                    raise cloud.CloudError(code)
            scope = {"CloudAPI": API, "CloudError": cloud.CloudError, "datetime": datetime,
                     "CONF_UUID": "uuid", "CONF_SESSION": "session",
                     "ConfigEntryAuthFailed": AuthFailed, "ConfigEntryNotReady": NotReady}
            method = extract_method("center.py", "CenterAPIv2", "_v2_refresh_session", scope)
            owner = types.SimpleNamespace(session=None, entry=types.SimpleNamespace(data={"uuid": "u"}))
            with self.assertRaises(expected):
                await method(owner)

    async def test_hub_closes_session_and_preserves_ha_errors(self):
        for expected in (AuthFailed, NotReady):
            class API:
                def __init__(self, *args):
                    pass
                async def start(self):
                    raise expected("safe error")
            scope = {"BestinCenterAPI": API, "ConfigEntryAuthFailed": AuthFailed,
                     "ConfigEntryNotReady": NotReady}
            method = extract_method("hub.py", "BestinHub", "async_initialize_center", scope)
            closed = []
            async def discard():
                closed.append(True)
            owner = types.SimpleNamespace(hass=None, entry=None, entity_groups={},hub_id="u",
                cntr_version="Smart Home 2.0", async_add_device_callback=None,
                _async_discard_api=discard)
            with self.assertRaises(expected):
                await method(owner)
            self.assertEqual(closed, [True])


if __name__ == "__main__":
    unittest.main()
