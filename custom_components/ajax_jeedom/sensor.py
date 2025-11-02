from .const  import DOMAIN
from .entity import get_list_of_sensors


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""
    hub = hass.data[DOMAIN][config_entry.entry_id]

    sensors = get_list_of_sensors('sensor', hub)
    async_add_entities(sensors)