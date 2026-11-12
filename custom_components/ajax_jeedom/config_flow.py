import hashlib
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, selector

from . import hub
from .market_api import MarketApi
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from .const import (
    CONF_AUTH_TOKEN,
    CONF_BASE_URL,
    CONF_PANIC_BUTTON,
    CONF_REPLACE_USERNAME,
    CONF_APPLY_HUB_STATE_TO_GROUPS,
    DOMAIN,
    LOGGER,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Required(
            CONF_AUTH_TOKEN, default=""
        ): cv.string,  # cv.matches_regex(r"^(oh)\.(.+)\.(.+)$"),
        vol.Required(CONF_PANIC_BUTTON, default=False): bool,
        vol.Required(CONF_REPLACE_USERNAME, default=True): bool,
        vol.Required(CONF_APPLY_HUB_STATE_TO_GROUPS, default=False): bool,
    }
)

options_schema = vol.Schema(
    {
        vol.Required(CONF_PANIC_BUTTON): bool,
        vol.Required(CONF_REPLACE_USERNAME): bool,
        vol.Required(CONF_APPLY_HUB_STATE_TO_GROUPS): bool,
    }
)


class AjaxConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Jeedom."""

    VERSION = 1

    async def async_step_jeedom(self, user_input=None):
        """Handle a flow initialized by the user."""

        errors = {}
        LOGGER.info("async_step_user")

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                # if info:
                # return await self.async_step_options(user_input)
                options = {
                    CONF_PANIC_BUTTON: user_input[CONF_PANIC_BUTTON],
                    CONF_REPLACE_USERNAME: user_input[CONF_REPLACE_USERNAME],
                    CONF_APPLY_HUB_STATE_TO_GROUPS: user_input[
                        CONF_APPLY_HUB_STATE_TO_GROUPS
                    ],
                }

                user_input.pop(CONF_PANIC_BUTTON, None)
                user_input.pop(CONF_REPLACE_USERNAME, None)
                user_input.pop(CONF_APPLY_HUB_STATE_TO_GROUPS, None)

                user_input["connection_type"] = "jeedom"
                if existing := getattr(self, "_existing", None):
                    return self.async_update_reload_and_abort(
                        existing, data_updates=user_input
                    )
                return self.async_create_entry(
                    title=info["title"], data=user_input, options=options
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidHost:
                # The error string is set here, and should be translated.
                # This example does not currently cover translations, see the
                # comments on `DATA_SCHEMA` for further details.
                # Set the error on the `host` field, not the entire form.
                errors["host"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="jeedom", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_user(self, user_input=None):
        return self.async_show_menu(step_id="user", menu_options=["jeedom", "market"])

    async def async_step_market(self, user_input=None):
        """Collect Market credentials and the existing event receiver."""
        existing = getattr(self, "_existing", None)
        defaults = dict(existing.data) if existing else {}
        errors = {}
        if user_input is not None:
            try:
                callback_url = cv.url(user_input["callback_url"])
            except vol.Invalid:
                errors["callback_url"] = "invalid_url"
            else:
                self._market_data = defaults
                self._market_data.update(
                    {
                        "connection_type": "market",
                        "callback_url": callback_url,
                        "market_login": user_input["market_login"],
                        "market_token": hashlib.sha512(
                            (
                                user_input["market_login"].lower()
                                + ":"
                                + hashlib.sha1(
                                    user_input["market_password"].encode()
                                ).hexdigest()
                            ).encode()
                        ).hexdigest(),
                    }
                )
                self._market_data[CONF_AUTH_TOKEN] = user_input[CONF_AUTH_TOKEN]
                self._market_data.setdefault(CONF_BASE_URL, callback_url)
                return await self.async_step_ajax()
        fields = {
            vol.Required("market_login"): cv.string,
            vol.Required("market_password"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required("callback_url"): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
            ),
        }
        fields[vol.Required(CONF_AUTH_TOKEN)] = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        )
        return self.async_show_form(
            step_id="market",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(fields), defaults
            ),
            errors=errors,
        )

    async def async_step_ajax(self, user_input=None):
        """Validate Ajax credentials without persisting them."""
        errors = {}
        existing = getattr(self, "_existing", None)
        if user_input is not None:
            data = dict(self._market_data)
            try:
                api = MarketApi(self.hass, data, existing)
                tokens = await api.login(
                    user_input["ajax_login"], user_input["ajax_password"]
                )
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except HomeAssistantError:
                errors["base"] = "cannot_connect"
            else:
                if existing:
                    await api.store.async_save(tokens)
                    data.pop("ajax_session", None)
                    return self.async_update_reload_and_abort(
                        existing, data_updates=data
                    )
                data["ajax_session"] = tokens
                return self.async_create_entry(title=data[CONF_BASE_URL], data=data)
        return self.async_show_form(
            step_id="ajax",
            data_schema=vol.Schema(
                {
                    vol.Required("ajax_login"): cv.string,
                    vol.Required("ajax_password"): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data):
        self._existing = self._get_reauth_entry()
        self._market_data = dict(entry_data)
        return await self.async_step_ajax()

    async def async_step_reconfigure(self, user_input=None):
        self._existing = self._get_reconfigure_entry()
        return self.async_show_menu(
            step_id="reconfigure", menu_options=["market", "jeedom"]
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                options_schema, self.config_entry.options
            ),
        )


async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # Validate the data can be used to set up a connection.

    # This is a simple example to show an error in the UI for a short hostname
    # The exceptions are defined at the end of this file, and are used in the
    # `async_step_user` method below.
    if len(data[CONF_BASE_URL]) < 3:
        raise InvalidHost

    # Test debug config
    if (data[CONF_BASE_URL] == "test") and (data[CONF_AUTH_TOKEN] == "test"):
        return {"title": "Virtual HUB"}

    result = await hub.ConfigFlowTestConnection(
        hass, data[CONF_BASE_URL], data[CONF_AUTH_TOKEN]
    )
    if not result:
        # If there is an error, raise an exception to notify HA that there was a
        # problem. The UI will also show there was a problem
        raise CannotConnect

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    # "Title" is what is displayed to the user for this hub device
    # It is stored internally in HA as part of the device config.
    # See `async_step_user` below for how this is used
    return {"title": data[CONF_BASE_URL]}


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid hostname."""
