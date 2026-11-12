"""Ajax requests through the Jeedom Market gateway."""

import asyncio
import json
import re
from urllib.parse import quote, quote_plus
import time

import aiohttp

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .const import DOMAIN, LOGGER


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
        response_text = ""
        status = None
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
                status = response.status
                response_text = await response.text()
                if response.status in (401, 403):
                    raise ConfigEntryAuthFailed("Jeedom Market authentication rejected")
                if response.status != 200:
                    raise HomeAssistantError(
                        f"Jeedom Market returned HTTP {response.status}"
                    )
                result = json.loads(response_text)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            self._log_error_response(method, path, status, response_text, data, token)
            raise HomeAssistantError("Unable to read Jeedom Market response") from err
        except HomeAssistantError:
            self._log_error_response(method, path, status, response_text, data, token)
            raise
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except ValueError as err:
                self._log_error_response(
                    method, path, status, response_text, data, token
                )
                raise HomeAssistantError("Invalid Jeedom Market response") from err
        if isinstance(result, dict) and (
            "error" in result or "errors" in result or result.get("state") == "nok"
        ):
            self._log_error_response(method, path, status, response_text, data, token)
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

    def _log_error_response(self, method, path, status, response_text, data, token):
        """Include the gateway response, with credentials removed."""
        secrets = [token]
        for source in (self.data, self.tokens, data or {}):
            for key, value in source.items():
                if re.search(
                    r"password|token|apikey|authorization|autorization", key, re.I
                ) and isinstance(value, str):
                    secrets.append(value)

        def collect_response_secrets(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if re.search(
                        r"password|token|apikey|authorization|autorization", key, re.I
                    ) and isinstance(item, str):
                        secrets.append(item)
                    else:
                        collect_response_secrets(item)
            elif isinstance(value, list):
                for item in value:
                    collect_response_secrets(item)
            elif isinstance(value, str):
                try:
                    nested = json.loads(value)
                except ValueError:
                    return
                if isinstance(nested, (dict, list)):
                    collect_response_secrets(nested)

        collect_response_secrets(response_text)
        body = response_text
        for secret in sorted(
            (value for value in secrets if value), key=len, reverse=True
        ):
            for value in {
                secret,
                quote(secret, safe=""),
                quote_plus(secret),
                json.dumps(secret)[1:-1],
            }:
                body = body.replace(value, "[redacted]")
        body = re.sub(
            r'(?i)("[^"\n]*(?:password|token|apikey|authorization|autorization)[^"\n]*"\s*:\s*)("(?:\\.|[^"\\])*"|[^,}\s]+)',
            r'\1"[redacted]"',
            body,
        )
        LOGGER.error(
            "Jeedom Market request failed: %s %s, HTTP %s, response: %s",
            method,
            path,
            status,
            body if response_text else "<empty or unavailable>",
        )

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
