'''Init.'''
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, SupportsResponse

from .ajax_service import AjaxService
from .const import DOMAIN
from .hub import AjaxHub

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH, Platform.BUTTON]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start Here."""
    h = AjaxHub(hass, entry.data, entry)
    entry.runtime_data = h

    # Load Ajax Devices
    await h.LoadAjaxDevices()

    # Add Sensors to Home Assistant
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Subscribe to incoimng data
    await h.Subscribe(hass)

    # Service call
    async def handle_arm_disarm(call):
        # LOGGER.info('handle_arm_disarm')
        return await AjaxService.handle_arm_disarm(hass, call) # type: ignore

    # register service
    hass.services.async_register(
        DOMAIN,
        "arm_disarm",
        handle_arm_disarm,
        supports_response=SupportsResponse.NONE,
    )

    # Options flow on change
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Update options from Integration Options Flow."""
    hub = entry.runtime_data
    hub.applyOptions(entry.options)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
