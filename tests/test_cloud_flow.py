"""Exercise real flow methods with an in-memory HA form/entry adapter."""
import ast
import asyncio
from pathlib import Path
import secrets
import re
import types
import unittest

import voluptuous as vol
import voluptuous_serialize
from test_cloud import cloud

ROOT = Path(__file__).resolve().parents[1] / "custom_components/bestin"


def load_without_ha(filename, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    tree.body = [v for v in tree.body if not isinstance(v, (ast.Import, ast.ImportFrom))]
    exec(compile(tree, str(ROOT / filename), "exec"), namespace)
    return namespace


class FakeAPI:
    def __init__(self):
        self.calls = []
        self.fail_register = self.fail_verify = self.fail_login = False

    async def complexes(self):
        self.calls.append("directory")
        return [{"code": "site", "name": "Test complex"}]

    async def register(self, *args):
        self.calls.append(("register", args))
        if self.fail_register:
            raise cloud.CloudError("network_error")
        return "transaction-secret"

    async def verify(self, transaction, code):
        self.calls.append(("verify", transaction, code))
        if self.fail_verify:
            raise cloud.CloudError("request_failed")

    async def login(self):
        self.calls.append("login")
        if self.fail_login:
            raise cloud.CloudError("network_error")
        return {"url": "https://site.example", "access-token": "token"}


ns = load_without_ha("cloud_flow.py", {"secrets": secrets, "re": re, "vol": vol,
    "CloudError": cloud.CloudError, "selector": lambda _: str})


class Flow(ns["CloudRegistrationFlow"]):
    def __init__(self):
        self.api = FakeAPI()

    def _cloud_api(self):
        return self.api

    def async_show_form(self, **kwargs):
        return {"type": "form", **kwargs}

    async def async_set_unique_id(self, value):
        self.unique_id = value

    def _abort_if_unique_id_configured(self):
        pass

    def async_create_entry(self, **kwargs):
        return {"type": "create_entry", **kwargs}

    def async_update_reload_and_abort(self, entry, **kwargs):
        return {"type": "abort", "entry": entry, **kwargs}


REGISTRATION = {"complex": "0", "dong": "101", "ho": "1203", "alias": "HA"}


class FlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_display_does_not_register(self):
        flow = Flow()
        form = await flow.async_step_cloud_register()
        self.assertEqual(flow.api.calls, ["directory"])
        values = form["data_schema"](REGISTRATION)
        self.assertEqual(values, REGISTRATION)
        # The same serializer used by HA must also be able to render the form.
        voluptuous_serialize.convert(form["data_schema"])

    async def test_invalid_registration_fields_do_not_send_requests(self):
        for field, value in (("complex", "999"), ("dong", "bad"), ("ho", ""),
                             ("alias", "morethan10characters")):
            flow = Flow()
            result = await flow.async_step_cloud_register({**REGISTRATION, field: value})
            self.assertIn(field, result["errors"])
            self.assertEqual(flow.api.calls, ["directory"])

    async def test_registration_retry_keeps_uuid(self):
        flow = Flow()
        flow.api.fail_register = True
        result = await flow.async_step_cloud_register(REGISTRATION)
        self.assertEqual(result["errors"], {"base": "cloud_network_error"})
        uuid = flow._cloud_uuid
        flow.api.fail_register = False
        result = await flow.async_step_cloud_register(REGISTRATION)
        self.assertEqual(flow._cloud_uuid, uuid)
        self.assertEqual(result["step_id"], "cloud_verify")
        self.assertEqual(len([c for c in flow.api.calls if isinstance(c, tuple)]), 2)

    async def test_new_code_is_explicit_and_preserves_uuid(self):
        flow = Flow()
        await flow.async_step_cloud_register(REGISTRATION)
        before = list(flow.api.calls)
        uuid = flow._cloud_uuid
        result = await flow.async_step_cloud_verify({"new_code": True})
        self.assertEqual(result["step_id"], "cloud_register")
        self.assertEqual(flow.api.calls, before)
        await flow.async_step_cloud_register(REGISTRATION)
        self.assertEqual(flow._cloud_uuid, uuid)

    async def test_verify_failure_and_login_retry_do_not_repeat_registration(self):
        flow = Flow()
        await flow.async_step_cloud_register(REGISTRATION)
        flow.api.fail_verify = True
        result = await flow.async_step_cloud_verify({"password": "123456"})
        self.assertEqual(result["step_id"], "cloud_verify")
        flow.api.fail_verify = False
        flow.api.fail_login = True
        result = await flow.async_step_cloud_verify({"password": "123456"})
        self.assertEqual(result["step_id"], "cloud_finish")
        calls = list(flow.api.calls)
        flow.api.fail_login = False
        result = await flow.async_step_cloud_finish({})
        self.assertEqual(flow.api.calls[len(calls):], ["login"])
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(set(result["data"]), {"uuid", "session"})
        self.assertNotIn("123456", str(result))
        self.assertNotIn("transaction-secret", str(result))

    async def test_bad_code_never_sent(self):
        flow = Flow()
        await flow.async_step_cloud_register(REGISTRATION)
        before = list(flow.api.calls)
        for code in ("", "12345", "abcdef", "１２３４５６"):
            form = await flow.async_step_cloud_verify({"password": code})
            self.assertEqual(form["errors"]["base"], "cloud_invalid_code")
        self.assertEqual(flow.api.calls, before)

    async def test_reauth_preserves_uuid_and_existing_entry(self):
        flow = Flow()
        flow._get_reauth_entry = lambda: "existing-entry"
        await flow.async_step_reauth({"uuid": "existing-device"})
        await flow.async_step_cloud_register(REGISTRATION)
        result = await flow.async_step_cloud_verify({"password": "123456"})
        self.assertEqual(flow._cloud_uuid, "existing-device")
        self.assertEqual(result["entry"], "existing-entry")
        self.assertEqual(set(result["data_updates"]), {"session"})


if __name__ == "__main__":
    unittest.main()
