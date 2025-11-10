"""buttons."""
from .entity import get_list_of_sensors


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add sensors for passed config_entry in HA."""
    hub = config_entry.runtime_data

    sensors = get_list_of_sensors("button", hub, config_entry)
    async_add_entities(sensors)
