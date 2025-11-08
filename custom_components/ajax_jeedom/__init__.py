from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, SupportsResponse, callback
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.event import async_track_time_interval

from .ajax_service import AjaxService
from .const import DOMAIN, LOGGER, PLATFORMS
from .hub import AjaxHub


def async_get_entities(hass: HomeAssistant):
    """Get entities for a domain."""
    entities = {}
    for platform in async_get_platforms(hass, DOMAIN):
        entities.update(platform.entities)
    return entities


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    h = AjaxHub(hass, entry.data, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = h

    await h.LoadAjaxDevices()
    await h.Subscribe(hass)

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_arm_disarm(call):
        # LOGGER.info('handle_arm_disarm')
        return await AjaxService.handle_arm_disarm(hass, call)

    hass.services.async_register(
        DOMAIN,
        "arm_disarm",
        handle_arm_disarm,
        supports_response=SupportsResponse.NONE,
    )

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    hub=hass.data.setdefault(DOMAIN, {})[entry.entry_id]
    hub.applyOptions(entry.options)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    return True
