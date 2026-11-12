"""Ajax requests through the Jeedom Market gateway."""

import asyncio
import json
import time

import aiohttp

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import DOMAIN


class MarketApi:
    """Keep a separate Ajax session, with serialized token rotation."""

    def __init__(self, hass, data, entry=None):
        self.hass = hass
        self.data = data
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self.tokens = dict(data.get("ajax_session", {}))
        self.store = (
            Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.session") if entry else None
        )
        self.lock = asyncio.Lock()
        self.expires = 0
        self.last_exec_error = ""

    async def _request(self, path, data, method, token=None):
        params = {"path": path}
        if token:
            params["session_token"] = token
        kwargs = {}
        if method == "GET":
            if data:
                params["options"] = json.dumps(data)
        else:
            kwargs["json"] = data
        try:
            async with self.session.request(
                method,
                "https://cloud.jeedom.com/service/ajaxSystem",
                params=params,
                headers={
                    "Autorization": self.data["market_token"],
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=60),
                **kwargs,
            ) as response:
                if response.status in (401, 403):
                    raise ConfigEntryAuthFailed("Jeedom Market authentication rejected")
                if response.status != 200:
                    raise HomeAssistantError(
                        f"Jeedom Market returned HTTP {response.status}"
                    )
                result = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise HomeAssistantError("Unable to read Jeedom Market response") from err
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except ValueError as err:
                raise HomeAssistantError("Invalid Jeedom Market response") from err
        if isinstance(result, dict) and (
            "error" in result or "errors" in result or result.get("state") == "nok"
        ):
            message = json.dumps(result).lower()
            if any(
                term in message
                for term in (
                    "wrong session",
                    "invalid refresh token",
                    "expired",
                    "not authorized",
                    "invalid password",
                    "wrong password",
                )
            ):
                raise ConfigEntryAuthFailed(
                    "Ajax authentication rejected; sign in again"
                )
            raise HomeAssistantError("Jeedom Market rejected the Ajax request")
        if isinstance(result, dict) and "body" in result:
            return result["body"]
        return result

    async def login(self, username, password):
        """Exchange credentials without storing the password."""
        result = await self._request(
            "/login",
            {
                "login": username,
                "passwordHash": password,
                "userRole": "USER",
                "url": self.data["callback_url"],
                "apikey": self.data["auth_token"],
            },
            "POST",
        )
        self._validate(result, login=True)
        self.tokens = {
            key: result[key] for key in ("userId", "sessionToken", "refreshToken")
        }
        self.expires = time.monotonic() + 14 * 60
        return self.tokens

    @staticmethod
    def _validate(result, login=False):
        keys = (
            ("userId", "sessionToken", "refreshToken")
            if login
            else ("sessionToken", "refreshToken")
        )
        if not isinstance(result, dict) or any(
            not isinstance(result.get(key), str) or not result[key] for key in keys
        ):
            raise HomeAssistantError("Incomplete Ajax session response")

    async def get_userId(self):
        """Load persisted tokens and return the account identifier."""
        if self.store:
            saved = await self.store.async_load()
            if saved:
                self.tokens = saved
            elif self.tokens:
                await self.store.async_save(self.tokens)
            if "ajax_session" in self.entry.data:
                entry_data = dict(self.entry.data)
                entry_data.pop("ajax_session")
                self.hass.config_entries.async_update_entry(self.entry, data=entry_data)
        if not self.tokens.get("userId"):
            raise ConfigEntryAuthFailed("Sign in to Ajax again")
        return self.tokens["userId"]

    async def get_config_json(self, path):
        return await self.exec_cmd(f"/user/{self.tokens['userId']}/{path}", {}, "GET")

    async def exec_cmd(self, path, data, call_method):
        """Refresh once under a lock; never replay a command after a timeout."""
        try:
            async with self.lock:
                if time.monotonic() >= self.expires:
                    result = await self._request(
                        "/refresh",
                        {
                            "userId": self.tokens["userId"],
                            "refreshToken": self.tokens["refreshToken"],
                        },
                        "POST",
                    )
                    self._validate(result)
                    self.tokens.update(
                        {key: result[key] for key in ("sessionToken", "refreshToken")}
                    )
                    if self.store:
                        await self.store.async_save(self.tokens)
                    self.expires = time.monotonic() + 14 * 60
                return await self._request(
                    path, data, call_method, self.tokens["sessionToken"]
                )
        except ConfigEntryAuthFailed:
            if self.entry:
                self.entry.async_start_reauth(self.hass)
            raise
