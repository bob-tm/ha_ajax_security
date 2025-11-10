from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv

from . import hub
from .const import (
    CONF_AUTH_TOKEN,
    CONF_BASE_URL,
    CONF_PANIC_BUTTON,
    CONF_REPLACE_USERNAME,
    CONF_APPLY_HUB_STATE_TO_GROUPS,
    DOMAIN,
    LOGGER,
)

DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_BASE_URL): str,
    vol.Required(CONF_AUTH_TOKEN, default=""): cv.string, # cv.matches_regex(r"^(oh)\.(.+)\.(.+)$"),
    vol.Required(CONF_PANIC_BUTTON, default=False): bool,
    vol.Required(CONF_REPLACE_USERNAME, default=True): bool,
    vol.Required(CONF_APPLY_HUB_STATE_TO_GROUPS, default=False): bool
    })

options_schema = vol.Schema({
    vol.Required(CONF_PANIC_BUTTON): bool,
    vol.Required(CONF_REPLACE_USERNAME): bool,
    vol.Required(CONF_APPLY_HUB_STATE_TO_GROUPS): bool
})

class AjaxConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Jeedom."""

    VERSION = 1

    async def async_step_user(self, user_input: None):
        """Handle a flow initialized by the user."""


        errors = {}
        LOGGER.info('async_step_user')
        LOGGER.info(user_input)

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                #if info:
                #return await self.async_step_options(user_input)
                options = {
                    CONF_PANIC_BUTTON               : user_input[CONF_PANIC_BUTTON],
                    CONF_REPLACE_USERNAME           : user_input[CONF_REPLACE_USERNAME],
                    CONF_APPLY_HUB_STATE_TO_GROUPS  : user_input[CONF_APPLY_HUB_STATE_TO_GROUPS]
                }

                user_input.pop(CONF_PANIC_BUTTON, None)
                user_input.pop(CONF_REPLACE_USERNAME, None)
                user_input.pop(CONF_APPLY_HUB_STATE_TO_GROUPS, None)

                return self.async_create_entry(title=info["title"], data=user_input, options=options)
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
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors
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
    if (data[CONF_BASE_URL]=='test') and (data[CONF_AUTH_TOKEN]=='test'):
        return {"title": 'Virtual HUB'}

    result = await hub.ConfigFlowTestConnection(data[CONF_BASE_URL], data[CONF_AUTH_TOKEN])
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