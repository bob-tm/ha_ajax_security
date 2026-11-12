"""Regression tests for the Market configuration form."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import unittest

import probatio

from homeassistant.helpers import config_validation as cv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from custom_components.ajax_jeedom.config_flow import AjaxConfigFlowHandler


class MarketFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_market_form_serialization(self) -> None:
        flow = AjaxConfigFlowHandler()
        flow.hass = MagicMock()
        result = await flow.async_step_market()
        fields = probatio.to_field_list(
            result["data_schema"], custom_serializer=cv.custom_serializer
        )
        callback_field = next(
            field for field in fields if field["name"] == "callback_url"
        )
        self.assertEqual(callback_field["selector"]["text"]["type"], "url")
        self.assertEqual(result["step_id"], "market")

    async def test_invalid_callback_does_not_login(self) -> None:
        flow = AjaxConfigFlowHandler()
        flow.hass = MagicMock()
        with (
            patch("custom_components.ajax_jeedom.market_api.async_get_clientsession"),
            patch(
                "custom_components.ajax_jeedom.config_flow.MarketApi.login",
                new_callable=AsyncMock,
            ) as login,
        ):
            result = await flow.async_step_market({"callback_url": "invalid"})
        self.assertEqual(result["errors"], {"callback_url": "invalid_url"})
        login.assert_not_awaited()

    async def test_two_step_login(self) -> None:
        flow = AjaxConfigFlowHandler()
        flow.hass = MagicMock()
        flow.hass.data = {}
        market_input = {
            "auth_token": "callback-key",
            "market_login": "MarketUser",
            "market_password": "market-secret",
            "callback_url": "https://example.com/jd/",
        }
        with (
            patch("custom_components.ajax_jeedom.market_api.async_get_clientsession"),
            patch(
                "custom_components.ajax_jeedom.config_flow.MarketApi.login",
                new_callable=AsyncMock,
                return_value={"userId": "u", "sessionToken": "s", "refreshToken": "r"},
            ) as login,
        ):
            result = await flow.async_step_market(market_input)
            login.assert_not_awaited()
            self.assertEqual(result["step_id"], "ajax")
            fields = probatio.to_field_list(
                result["data_schema"], custom_serializer=cv.custom_serializer
            )
            self.assertEqual(
                {field["name"] for field in fields}, {"ajax_login", "ajax_password"}
            )
            result = await flow.async_step_ajax(
                {"ajax_login": "ajax-user", "ajax_password": "ajax-secret"}
            )
        login.assert_awaited_once_with("ajax-user", "ajax-secret")
        self.assertEqual(result["data"]["connection_type"], "market")
        self.assertEqual(result["data"]["auth_token"], "callback-key")
        self.assertEqual(
            result["data"]["market_token"],
            "fcd013420593ca8ee9fbdc46b39cef7373a8c6688ce91517042763419d89d0bd4a12edd7c2b13b582628396e2904cfa78c20f90e1b744d6ff1787b8fe9915d10",
        )
        self.assertNotIn("market_password", result["data"])
        self.assertNotIn("ajax_password", result["data"])
        self.assertNotIn("ajax_login", result["data"])

    async def test_reauth_only_requests_ajax_credentials(self) -> None:
        flow = AjaxConfigFlowHandler()
        flow.hass = MagicMock()
        flow._get_reauth_entry = MagicMock()
        result = await flow.async_step_reauth({"market_token": "existing-token"})
        self.assertEqual(result["step_id"], "ajax")

    async def test_regular_setup_reports_device_progress(self) -> None:
        from custom_components.ajax_jeedom.hub import AjaxHub

        hub = AjaxHub.__new__(AjaxHub)
        hub._host = "https://example.com"
        hub._apikey = "key"
        hub.config_entry = MagicMock(data={"connection_type": "market"})
        hub.hass = MagicMock()
        hub.hass.async_add_executor_job = AsyncMock(return_value=False)
        hub.hubs = {}
        hub.GetUserIdFromCacheOrApi = AsyncMock(return_value="user")
        responses = {
            "hubs": [{"hubId": "hub"}],
            "hubs/hub": {"name": "Home"},
            "hubs/hub/groups": [],
            "hubs/hub/devices": [{"id": "device", "deviceName": "Motion"}],
            "hubs/hub/devices/device": {"deviceName": "Motion"},
            "hubs/hub/rooms": [],
        }
        hub.GetFromCacheOrApi = AsyncMock(
            side_effect=lambda path, *args: responses[path]
        )
        hub.create_device = MagicMock()
        progress = MagicMock()
        with (
            patch("custom_components.ajax_jeedom.hub.MarketApi") as api,
            patch(
                "custom_components.ajax_jeedom.hub.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            api.return_value.get_userId = AsyncMock(return_value="user")
            await hub.LoadAjaxDevices(progress)
        progress.assert_any_call("Хаб Home: читаем устройство 1 из 1 — Motion")
        progress.assert_any_call("Хаб Home: прочитано 1 из 1 — Motion")
        self.assertEqual(hub.GetFromCacheOrApi.await_count, len(responses))
