"""Alarm control panel entities for Ajax hubs and groups."""

from __future__ import annotations

import asyncio

from homeassistant.components.alarm_control_panel import AlarmControlPanelEntity
from homeassistant.components.alarm_control_panel.const import (
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities: AddConfigEntryEntitiesCallback):
    """Set up Ajax alarm control panels from a config entry."""
    hub = config_entry.runtime_data
    entities: list[AjaxAlarmControlPanel] = []

    for hub_data in hub.hubs.values():
        hub_device = hub_data["hubAjax"]
        entities.append(AjaxAlarmControlPanel(hub_device, config_entry, is_hub=True))

        for device in hub_data["devices"].values():
            if device.devicetype == "GROUP":
                entities.append(
                    AjaxAlarmControlPanel(device, config_entry, is_hub=False)
                )

    async_add_entities(entities)


class AjaxAlarmControlPanel(AlarmControlPanelEntity):
    """Expose an Ajax hub or group as a Home Assistant alarm panel."""

    _attr_should_poll = False
    _attr_code_arm_required = False

    def __init__(self, ajax_device, config_entry, *, is_hub: bool) -> None:
        """Initialize the alarm control panel."""
        self._ad = ajax_device
        self._config_entry_id = config_entry.entry_id
        self._is_hub = is_hub

        if is_hub:
            self._state_sensor_name = "hub_state"
            self._extra_state_sensors = ("night_mode_armed",)
            self._attr_name = ajax_device.name
            self._attr_supported_features = (
                AlarmControlPanelEntityFeature.ARM_AWAY
                | AlarmControlPanelEntityFeature.ARM_NIGHT
            )
            self._attr_unique_id = f"{ajax_device.parentHubId}.{ajax_device.id}_alarm_panel"
        else:
            self._state_sensor_name = "state"
            self._extra_state_sensors = ()
            self._attr_name = f"{ajax_device.name} Alarm"
            self._attr_supported_features = AlarmControlPanelEntityFeature.ARM_AWAY
            self._attr_unique_id = (
                f"{ajax_device.parentHubId}.{ajax_device.id}_group_alarm_panel"
            )

        self._ad.register_sensor(self._state_sensor_name)
        for sensor_name in self._extra_state_sensors:
            self._ad.register_sensor(sensor_name)

    @property
    def device_info(self):
        """Return information to link this entity with the correct device."""
        return {"identifiers": {(self._ad.id, DOMAIN)}}

    @property
    def available(self) -> bool:
        """Return whether the device is available."""
        return self._ad.online

    @property
    def extra_state_attributes(self) -> dict[str, str | bool | None]:
        """Return additional diagnostic state."""
        attrs: dict[str, str | bool | None] = {
            "ajax_state": self._ad.get_sensor_value(self._state_sensor_name),
            "ajax_device_type": self._ad.devicetype,
        }
        if self._is_hub:
            attrs["night_mode_armed"] = self._ad.get_sensor_value("night_mode_armed")
            attrs["night_mode_state"] = self._ad.get_sensor_value("night_mode_state")
        return attrs

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current Home Assistant alarm state."""
        raw_state = self._ad.get_sensor_value(self._state_sensor_name)

        if self._is_hub and self._ad.get_sensor_value("night_mode_armed"):
            if raw_state == "Disarmed":
                return AlarmControlPanelState.ARMED_NIGHT

        mapping = {
            "Armed": AlarmControlPanelState.ARMED_AWAY,
            "ArmedWithErrors": AlarmControlPanelState.ARMED_AWAY,
            "Disarmed": AlarmControlPanelState.DISARMED,
            "PartiallyArmed": AlarmControlPanelState.ARMED_HOME,
            "ArmAttempt": AlarmControlPanelState.ARMING,
            "Request": AlarmControlPanelState.PENDING,
        }
        return mapping.get(raw_state)

    async def async_added_to_hass(self) -> None:
        """Register callbacks when the entity is added."""
        self._ad.register_callback(self._state_sensor_name, self.async_write_ha_state)
        for sensor_name in self._extra_state_sensors:
            self._ad.register_callback(sensor_name, self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Remove callbacks when the entity is removed."""
        self._ad.remove_callback(self._state_sensor_name, self.async_write_ha_state)
        for sensor_name in self._extra_state_sensors:
            self._ad.remove_callback(sensor_name, self.async_write_ha_state)

    async def _async_run_command(self, command: str) -> None:
        """Run an Ajax command through the shared device command path."""
        await self._ad.exec_command(command, self._context)

    def _run_command(self, command: str) -> None:
        """Run an Ajax command from a sync alarm entity method."""
        asyncio.run_coroutine_threadsafe(
            self._async_run_command(command), self.hass.loop
        ).result()

    def alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        self._run_command("DISARM")

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self._async_run_command("DISARM")

    def alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        self._run_command("ARM")

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self._async_run_command("ARM")

    def alarm_arm_night(self, code: str | None = None) -> None:
        """Send night arm command for the hub."""
        if not self._is_hub:
            return
        self._run_command("NIGHT_MODE_ON")

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        """Send night arm command for the hub."""
        if not self._is_hub:
            return
        await self._async_run_command("NIGHT_MODE_ON")
