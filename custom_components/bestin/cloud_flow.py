"""In-HA wallpad registration; verification secrets stay in the flow only."""
from __future__ import annotations

import secrets
import re

import voluptuous as vol
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import selector

from .cloud import CloudAPI, CloudError


class CloudRegistrationFlow:
    """Mixin for the existing BESTIN config flow."""

    def _cloud_api(self):
        return CloudAPI(async_get_clientsession(self.hass), getattr(self, "_cloud_uuid", ""))

    async def async_step_reauth(self, entry_data):
        self._cloud_reauth_entry = self._get_reauth_entry()
        self._cloud_uuid = entry_data["uuid"]
        return await self.async_step_cloud_register()

    async def async_step_cloud_register(self, user_input=None):
        errors = {}
        if not hasattr(self, "_cloud_complexes"):
            try:
                self._cloud_complexes = await self._cloud_api().complexes()
            except CloudError as exc:
                return self.async_show_form(step_id="cloud_register", data_schema=vol.Schema({}),
                                            errors={"base": "cloud_" + str(exc)})
        choices = {str(i): f"{v.get('location', '')} {v['name']}".strip()
                   for i, v in enumerate(self._cloud_complexes)}
        if user_input is not None and "complex" in user_input:
            self._cloud_registration = dict(user_input)
            if user_input["complex"] not in choices:
                errors["complex"] = "cloud_invalid_complex"
            for field, pattern in (("dong", r"[1-9][0-9]*"), ("ho", r"[1-9][0-9-]*"),
                                   ("alias", r"[가-힣ㄱ-ㅎA-Za-z0-9~!@#$%+.?]{1,10}")):
                if not re.fullmatch(pattern, user_input.get(field, "")):
                    errors[field] = "cloud_invalid_" + field
        if user_input is not None and "complex" in user_input and not errors:
            # Generate once per flow, including retries after a lost response.
            if not hasattr(self, "_cloud_uuid"):
                self._cloud_uuid = (f"{secrets.token_hex(2)}-{secrets.token_hex(2)}-"
                                    f"9{secrets.token_hex(2)[:3]}-"
                                    f"{secrets.choice('89ab')}{secrets.token_hex(2)[:3]}-{secrets.token_hex(2)}")
            site = self._cloud_complexes[int(user_input["complex"])]
            self._cloud_site_name = site["name"]
            try:
                self._cloud_transaction = await self._cloud_api().register(
                    site["code"], user_input["dong"], user_input["ho"], user_input["alias"],
                )
                return await self.async_step_cloud_verify()
            except CloudError as exc:
                errors["base"] = "cloud_" + str(exc)
        defaults = getattr(self, "_cloud_registration", {})
        return self.async_show_form(step_id="cloud_register", errors=errors, data_schema=vol.Schema({
            vol.Required("complex", default=defaults.get("complex", "0")): selector({
                "select": {"options": [{"value": k, "label": v} for k, v in choices.items()],
                           "mode": "dropdown", "custom_value": False}}),
            vol.Required("dong", default=defaults.get("dong", "")): selector({"text": {}}),
            vol.Required("ho", default=defaults.get("ho", "")): selector({"text": {}}),
            vol.Required("alias", default=defaults.get("alias", "HA")): selector({"text": {}}),
        }))

    async def async_step_cloud_verify(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input.get("new_code"):
                # Returning to the explicit registration form does not send another request.
                return await self.async_step_cloud_register()
            code = user_input.get("password", "").strip()
            if len(code) != 6 or not code.isascii() or not code.isdigit():
                errors["base"] = "cloud_invalid_code"
            else:
                try:
                    await self._cloud_api().verify(self._cloud_transaction, code)
                    self._cloud_verified = True
                    return await self.async_step_cloud_finish({})
                except CloudError as exc:
                    errors["base"] = "cloud_" + str(exc)
        return self.async_show_form(step_id="cloud_verify", errors=errors, data_schema=vol.Schema({
            vol.Optional("password"): selector({"text": {"type": "password"}}),
            vol.Optional("new_code", default=False): bool,
        }))

    async def async_step_cloud_finish(self, user_input=None):
        if not getattr(self, "_cloud_verified", False):
            return await self.async_step_cloud_register()
        errors = {}
        if user_input is not None:
            try:
                session = await self._cloud_api().login()
            except CloudError as exc:
                errors["base"] = "cloud_" + str(exc)
            else:
                if hasattr(self, "_cloud_reauth_entry"):
                    return self.async_update_reload_and_abort(
                        self._cloud_reauth_entry, data_updates={"session": session},
                    )
                await self.async_set_unique_id(self._cloud_uuid)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=self._cloud_site_name, data={
                    "uuid": self._cloud_uuid, "session": session,
                })
        return self.async_show_form(step_id="cloud_finish", data_schema=vol.Schema({}), errors=errors)
