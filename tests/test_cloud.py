"""Offline protocol tests; run directly without Home Assistant."""
import asyncio
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cloud", ROOT / "custom_components/bestin/cloud.py")
cloud = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cloud)


class Response:
    def __init__(self, body, status=200):
        self.body, self.status = body, status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def json(self, **kwargs):
        return self.body


class Session:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class CloudTests(unittest.IsolatedAsyncioTestCase):
    async def test_doors_and_open_wire_format(self):
        session = Session(Response([{"id": 0, "lobby_name": "정문"},
                                    {"id": "a/b", "lobby_name": "후문"}]), Response({"result": "ok"}))
        api = cloud.CloudAPI(session)
        auth = {"url": "https://site.example", "access-token": "secret", "alias": "HA"}
        self.assertEqual(await api.doors(auth), [{"id": "0", "lobby_name": "정문"},
                                                {"id": "a/b", "lobby_name": "후문"}])
        await api.open_door(auth, "a/b")
        self.assertEqual(session.calls[0][0:2], ("GET", "https://site.example/v2/api/onepass/doors"))
        self.assertEqual(session.calls[1][0:2], ("POST", "https://site.example/v2/api/onepass/doors/a%2Fb/apply"))
        self.assertEqual(session.calls[1][2]["json"], {"appname": "스마트홈2.0", "alias": "HA"})
        self.assertEqual(session.calls[1][2]["headers"]["access-token"], "secret")

    async def test_door_invalid_inputs_and_responses(self):
        auth = {"url": "https://site.example", "access-token": "t"}
        for body in ({}, [None], [{"id": True, "lobby_name": "X"}],
                     [{"id": "", "lobby_name": "X"}], [{"id": "1"}],
                     [{"id": 1, "lobby_name": "A"}, {"id": "1", "lobby_name": "B"}]):
            with self.assertRaises(cloud.CloudError):
                await cloud.CloudAPI(Session(Response(body))).doors(auth)
        self.assertEqual(await cloud.CloudAPI(Session(Response([]))).doors(auth), [])
        session = Session()
        with self.assertRaises(cloud.CloudError):
            await cloud.CloudAPI(session).open_door(auth, "1")
        self.assertEqual(session.calls, [])
        for body in ({}, [], {"result": "fail"}, {"result": "unknown"}):
            session = Session(Response(body))
            with self.assertRaises(cloud.CloudError):
                await cloud.CloudAPI(session).open_door({**auth, "alias": "HA"}, "1")
            self.assertEqual(len(session.calls), 1)
        session = Session(asyncio.TimeoutError())
        with self.assertRaises(cloud.CloudError):
            await cloud.CloudAPI(session).open_door({**auth, "alias": "HA"}, "1")
        self.assertEqual(len(session.calls), 1)

    def test_onepass_support(self):
        self.assertIsNone(cloud.onepass_support({}))
        self.assertIs(cloud.onepass_support({"additional": []}), False)
        self.assertIs(cloud.onepass_support({"additional": '[{"category":"onepass"}]'}), True)

    async def test_registration_verify_login_wire_format(self):
        session = Session(Response({"transaction": "tx"}), Response({"result": "ok"}),
                          Response({"url": "https://site.example", "access-token": "token"}))
        api = cloud.CloudAPI(session, "device")
        self.assertEqual(await api.register("site", "101", "1203", "HA"), "tx")
        await api.verify("tx", "123456")
        result = await api.login()
        self.assertEqual(result["access-token"], "token")
        self.assertEqual(session.calls[0][2]["json"],
                         {"type": "homedev", "site": "site", "identifier": "101/1203", "alias": "HA"})
        self.assertEqual(session.calls[1][2]["json"], {"transaction": "tx", "password": "123456"})
        for _, _, kwargs in session.calls:
            self.assertEqual(kwargs["headers"]["Authorization"], "device")
            self.assertTrue(kwargs["headers"]["X-API-KEY"])
            self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(session.calls[2][2]["data"], "V2")

    async def test_elevator_no_address_and_both_directions(self):
        session = Session(Response({"result": "ok"}), Response({"result": "ok"}))
        api = cloud.CloudAPI(session)
        auth = {"url": "https://site.example", "access-token": "secret"}
        for direction in ("up", "down"):
            await api.call_elevator(auth, direction)
        for (method, url, kwargs), direction in zip(session.calls, ("up", "down")):
            self.assertEqual(method, "POST")
            self.assertEqual(url, "https://site.example/v2/api/elevator/" + direction)
            self.assertEqual(kwargs["data"], direction)
            self.assertNotIn("json", kwargs)
            self.assertEqual(kwargs["headers"]["access-token"], "secret")
        with self.assertRaises(ValueError):
            await api.call_elevator(auth, "cancel")
        self.assertEqual(len(session.calls), 2)

    async def test_errors_never_retry_or_leak_payload(self):
        for response in (Response({"result": "fail", "secret": "secret"}),
                         Response({"err": {"msg": "secret"}}),
                         Response({}, 401), Response({}, 302), asyncio.TimeoutError()):
            session = Session(response)
            with self.assertRaises(cloud.CloudError) as raised:
                await cloud.CloudAPI(session).call_elevator(
                    {"url": "https://site.example", "access-token": "secret"}, "down")
            self.assertNotIn("secret", str(raised.exception))
            self.assertEqual(len(session.calls), 1)

    async def test_malformed_registration_and_login(self):
        for body in ({}, [], {"url": "https://site.example"},
                     {"url": "https://user:pass@site.example", "access-token": "t"}):
            with self.assertRaises(cloud.CloudError):
                await cloud.CloudAPI(Session(Response(body)), "id").login()
        with self.assertRaises(cloud.CloudError):
            await cloud.CloudAPI(Session(Response({})), "id").register("s", "1", "2", "HA")

    def test_url_validation(self):
        for url in ("file:///etc/passwd", "https://u:p@example.com", "https://example.com/#frag",
                    "https://example.com/?token=x", "https://example.com/path", "//example.com"):
            with self.assertRaises(cloud.CloudError):
                cloud.validate_session({"url": url, "access-token": "t"})

    def test_capabilities_missing_malformed_and_explicit(self):
        for value in ({}, {"additional": None}, {"additional": "bad"}, {"additional": {}}):
            self.assertIsNone(cloud.elevator_support(value))
        for value in ([], '[{"category":"onepass"}]'):
            self.assertIs(cloud.elevator_support({"additional": value}), False)
        for value in ([{"category": "elevator"}], '[{"category":"elevator"}]'):
            self.assertIs(cloud.elevator_support({"additional": value}), True)


if __name__ == "__main__":
    unittest.main()
