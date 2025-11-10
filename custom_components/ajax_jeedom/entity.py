'''HA sensors.'''
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.helpers.entity import Any, Entity

from .ajax_devices_schema import BinarySensors, Diagnostic

#from homeassistant.util.unit_system import TEMPERATURE_UNITS
from .const import DOMAIN


def get_list_of_sensors(platform, hub, config_entry):
    '''Get list of sensors to platform setup.'''
    sensors = []

    for h in hub.hubs:
        devices = hub.hubs[h]["devices"]

        if platform == "switch":
            for ad in devices.values():
                for a in ad.Switches:
                    sensors.append(SwitchBase(ad, a, platform, config_entry))
        elif platform == "button":
            for ad in devices.values():
                for a in ad.Actions:
                    sensors.append(ButtonBase(ad, a, platform, config_entry))
        else:
            for ad in devices.values():
                for s in ad.SensorsVisible:
                    if s in BinarySensors:
                        if platform == "binary_sensor":
                            sensors.append(SensorBase(ad, s, platform, config_entry))
                    elif platform == "sensor":
                        sensors.append(SensorBase(ad, s, platform, config_entry))

    return sensors


class SensorBase(Entity):
    '''HA Sensor Class.'''
    _attr_should_poll = False

    def __init__(self, ad, sensor_name, platform, config_entry)->None:
        '''Init.'''
        hubName = ad.parentHub.name if ad.parentHub else ""
        self._ad = ad
        self._is_binary = platform == "binary_sensor"
        self.sensor_name = sensor_name
        self._config_entry_id = config_entry.entry_id
        # self._attr_unique_id    = f"{self._ad.id}_{self.sensor_name}"
        self._attr_unique_id = (
            f"{self._ad.parentHubId}.{self._ad.id}_{self.sensor_name}"
        )
        self._attr_name = self.sensor_name
        # self.entity_id          = f"{platform}.{self._ad.id}_{self.sensor_name}"
        # self.entity_id          = f"{platform}.{ad.name}_{self.sensor_name}"
        self.entity_id = f"{platform}.{hubName}_{ad.name}_{self.sensor_name}"

        ad.register_sensor(self.sensor_name)

        if self.sensor_name == "temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_unit_of_measurement = UnitOfTemperature.CELSIUS
        elif self.sensor_name == "batteryCharge":
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_unit_of_measurement = "%"
        elif self.sensor_name == "voltageVolts":
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_unit_of_measurement = "V"
        elif self.sensor_name == "currentMA":
            self._attr_device_class = SensorDeviceClass.CURRENT
            self._attr_unit_of_measurement = "mA"
        elif self.sensor_name == "powerWtH":
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_unit_of_measurement = "Wh"
        elif self.sensor_name == "voltageMilliVolts":
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_unit_of_measurement = "mV"
        elif self.sensor_name in ["reedClosed", "extraContactClosed"]:
            self._attr_device_class = BinarySensorDeviceClass.WINDOW
        elif self.sensor_name in ["tampered"]:
            self._attr_device_class = BinarySensorDeviceClass.TAMPER

    def get_ajax_device(self):
        '''Return parent Ajax Device.'''
        return self._ad

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(self._ad.id, DOMAIN)}}

    @property
    def entity_category(self):
        '''Category.'''
        if self.sensor_name in Diagnostic:
            return EntityCategory.DIAGNOSTIC
        else:
            return None

    # This property is important to let HA know if this entity is online or not.
    # If an entity is offline (return False), the UI will refelect this.
    @property
    def available(self) -> bool:
        '''A.'''
        x = self._ad.online
        # print(f"{self._ad.name} online is {x}")

        return x

    async def async_added_to_hass(self):
        """Run when this Entity has been added to HA."""
        # Sensors should also register callbacks to HA when their state changes
        self._ad.register_callback(self.sensor_name, self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._ad.remove_callback(self.sensor_name, self.async_write_ha_state)

    @property
    def state(self):
        '''State.'''
        x = self._ad.get_sensor_value(self.sensor_name)
        if self._is_binary:
            if x is not None:
                return int(x) == 1
        return x


class ButtonBase(SensorBase, ButtonEntity):
    '''Buttons.'''
    async def async_press(self):
        '''Press Action.'''
        result = await self._ad.exec_command(self.sensor_name, self._context)
        return result

    @property
    def state(self):
        '''State for button.'''
        return self.sensor_name


class SwitchBase(SensorBase, SwitchEntity):
    '''Switch.'''
    async def async_added_to_hass(self):
        '''Register callback on state sensor update.'''
        sn = self._ad.Switches[self.sensor_name]["state_sensor_name"]
        self._ad.register_callback(sn, self.async_write_ha_state)

    async def async_will_remove_from_hass(self):
        '''UnRegister callback on state sensor update.'''
        sn = self._ad.Switches[self.sensor_name]["state_sensor_name"]
        self._ad.remove_callback(sn, self.async_write_ha_state)

    @property
    def state(self):
        '''Switch State.'''
        is_on = self._ad.get_switch_is_on(self.sensor_name)
        return "on" if is_on else "off"

    @property
    def is_on(self) -> bool | None:
        '''Is On.'''
        return self._ad.get_switch_is_on(self.sensor_name)

    async def async_turn_on(self, **kwargs: dict[str, Any]) -> None:
        '''Turn On Action.'''
        cmd_on = self._ad.Switches[self.sensor_name]["on"]
        await self._ad.exec_command(cmd_on, self._context)

    async def async_turn_off(self, **kwargs: dict[str, Any]) -> None:
        '''Turn Off Action.'''
        cmd_off = self._ad.Switches[self.sensor_name]["off"]
        await self._ad.exec_command(cmd_off, self._context)
