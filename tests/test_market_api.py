import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError

package = types.ModuleType("ajax_market_test")
package.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components/ajax_jeedom")
]
sys.modules[package.__name__] = package
spec = importlib.util.spec_from_file_location(
    "ajax_market_test.market_api", Path(package.__path__[0]) / "market_api.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MarketTests(unittest.IsolatedAsyncioTestCase):
    def make_api(self):
        with patch.object(module, "async_get_clientsession"):
            api = module.MarketApi(
                MagicMock(),
                {
                    "market_token": "market",
                    "callback_url": "https://example.com/jd",
                    "auth_token": "callback",
                },
            )
        api.tokens = {
            "userId": "user",
            "sessionToken": "old",
            "refreshToken": "refresh",
        }
        api.store = MagicMock()
        api.store.async_save = AsyncMock()
        return api

    async def test_concurrent_refresh(self) -> None:
        api = self.make_api()

        async def request(
            path: str, data: dict, method: str, token: str | None = None
        ) -> dict:
            await asyncio.sleep(0)
            if path == "/refresh":
                return {"sessionToken": "new", "refreshToken": "rotated"}
            self.assertEqual(token, "new")
            api.store.async_save.assert_awaited_once()
            return {"ok": True}

        api._request = AsyncMock(side_effect=request)
        await asyncio.gather(
            api.exec_cmd("/one", {}, "GET"), api.exec_cmd("/two", {}, "GET")
        )
        self.assertEqual(
            sum(call.args[0] == "/refresh" for call in api._request.await_args_list), 1
        )
        self.assertEqual(api.tokens["refreshToken"], "rotated")

    async def test_rejected_refresh_starts_reauth(self) -> None:
        api = self.make_api()
        api.entry = MagicMock()
        api._request = AsyncMock(side_effect=ConfigEntryAuthFailed("rejected"))
        with self.assertRaises(ConfigEntryAuthFailed):
            await api.exec_cmd("/command", {}, "PUT")
        api.entry.async_start_reauth.assert_called_once_with(api.hass)
        api.store.async_save.assert_not_awaited()

    async def test_timeout_does_not_replay_command(self) -> None:
        api = self.make_api()
        api.expires = float("inf")
        api._request = AsyncMock(side_effect=HomeAssistantError("timeout"))
        with self.assertRaises(HomeAssistantError):
            await api.exec_cmd("/command", {}, "PUT")
        api._request.assert_awaited_once()

    async def test_login_does_not_store_password(self) -> None:
        api = self.make_api()
        api._request = AsyncMock(
            return_value={"userId": "u", "sessionToken": "s", "refreshToken": "r"}
        )
        tokens = await api.login("login", "secret")
        self.assertEqual(set(tokens), {"userId", "sessionToken", "refreshToken"})
        self.assertNotIn("secret", str(api.data))
        self.assertEqual(api._request.call_args.args[1]["passwordHash"], "secret")
        self.assertEqual(
            api._request.call_args.args[1]["url"], "https://example.com/jd"
        )


if __name__ == "__main__":
    unittest.main()
