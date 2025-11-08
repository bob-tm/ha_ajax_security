"""Hun Integration for Ajax Security"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import time

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.util import utcnow

from .const import (
    CONF_API_URL,
    CONF_APPLY_HUB_STATE_TO_GROUPS,
    CONF_AUTH_TOKEN,
    CONF_BASE_URL,
    CONF_PANIC_BUTTON,
    CONF_REPLACE_USERNAME,
    DOMAIN,
    LOGGER,
    PLATFORMS,
    SWITCH_ENABLED,
)
from .JeedomAjaxApi import JeedomAjaxApi
from .mqtt_raw_event_parser import (
    STATE_ARMATTEMPT,
    STATE_ARMED,
    STATE_ARMED_WITH_ERRORS,
    STATE_DISARMED,
    STATE_EXEC_CMD,
    STATE_HUB_CHECK_GROUPS,
    STATE_HUB_PARTIALLY_ARMED,
    AjaxHubEventSensors,
    HubStateToLowerCaseState,
    SensorNameFromLogToConfig,
    parse_raw_message,
)
from .utils import strip_ip

CACHE_AJAX_REQUESTS = False
#CACHE_AJAX_REQUESTS = True


async def ConfigFlowTestConnection(host, token):
    try:
        japi = JeedomAjaxApi(host.rstrip("\\"), CONF_API_URL, token)
        r = await japi.isOk()
        return r
    except:
        return False


class AjaxHub:
    manufacturer = "Ajax"

    def __init__(self, hass: HomeAssistant, entry_data, config_entry) -> None:
        self.disk_cache = CACHE_AJAX_REQUESTS
        self._apikey    = entry_data[CONF_AUTH_TOKEN]
        self._host      = entry_data[CONF_BASE_URL].rstrip("\\")
        self._apiurl    = CONF_API_URL

        self._hass = hass
        self._name = self._host
        self._id = self._host.lower()
        self.devices = {}
        self.rooms   = {}
        self.groups  = {}
        self.hubs    = {}

        self.enable_panic_button              = False
        self.enable_ha_user_replace           = True
        self.enable_apply_hub_state_to_groups = False
        self.applyOptions(config_entry.options)

        self.replace_api_addr_before_call = False
        # debug feature to test bad url for testing
        # self.replace_api_addr_before_call = 'https://google.com/sdf'

        self._ha_lastaction_user = None
        self._ha_lastaction_time = 0

        # patched Jeedom Ajax Plugin
        self.ajax_user_id = False  # user id for direct API call

        self.config_entry = config_entry
        self.online = True

        # if self.disk_cache:
        self.cache_folder = (
            hass.config.path(STORAGE_DIR, DOMAIN)
            + os.sep
            + strip_ip(self._host.lower())
        )
        os.makedirs(self.cache_folder, exist_ok=True)

    def applyOptions(self, options):
        self.enable_panic_button              = options.get(CONF_PANIC_BUTTON,              self.enable_panic_button)
        self.enable_ha_user_replace           = options.get(CONF_REPLACE_USERNAME,          self.enable_ha_user_replace)
        self.enable_apply_hub_state_to_groups = options.get(CONF_APPLY_HUB_STATE_TO_GROUPS, self.enable_apply_hub_state_to_groups)

    def setUserNameFromId(self, user_id):
        persons = self._hass.states.all('person')
        for p in persons:
            if user_id==p.attributes['user_id']:
                self._ha_lastaction_user = p.name
                self._ha_lastaction_time = time.time()

                return

        self._ha_lastaction_user = None
        self._ha_lastaction_time = 0

    async def setContextFromLastCall(self, context):
        await self._hass.async_add_executor_job(self.setUserNameFromId, context.user_id)

    def getCachedJsonFile(self, filename):
        if not self.disk_cache:
            return False

        fn = self.cache_folder + os.sep + filename
        if not os.path.exists(fn):
            return False

        with open(fn) as json_data:
            return json.load(json_data)

    def saveJsonToCache(self, filename, data):
        # if not self.disk_cache:
        #    return False

        fn = self.cache_folder + os.sep + filename
        path = Path(fn)
        os.makedirs(path.parent.absolute(), exist_ok=True)

        json_str = json.dumps(data, indent=4)
        with open(fn, "w") as f:
            f.write(json_str)

    async def GetFromCacheOrApi(self, path):
        file_cache = f"{self.ajax_user_id}/{path}.json"
        r = self.getCachedJsonFile(file_cache)
        if not r:
            r = await self.ajax_api.get_config_json(path)
            if r:
                self.saveJsonToCache(file_cache, r)

        return r

    async def GetUserIdFromCacheOrApi(self):
        file_cache = "userid.json"
        r = self.getCachedJsonFile(file_cache)
        if not r:
            r = {}
            r["userid"] = await self.ajax_api.get_userId()
            if r:
                self.saveJsonToCache(file_cache, r)

        return r["userid"]

    async def LoadAjaxDevices(self):
        self.ajax_api = JeedomAjaxApi(self._host, self._apiurl, self._apikey)
        self.ajax_user_id = await self.GetUserIdFromCacheOrApi()
        if self.ajax_user_id == False:
            LOGGER.error(
                f"Can not get Ajax UserId: Check if Patch is applied and ajax token is correct"
            )
            return

        # ajax={}
        hubs = await self.GetFromCacheOrApi("hubs")
        if hubs:
            # ajax['hubs']=hubs
            for h in hubs:
                hubId = h["hubId"]
                hub_info = await self.GetFromCacheOrApi(f"hubs/{hubId}")
                if hub_info:
                    # ajax['hubs'][hubId]=info
                    HubAjax = self.create_device(hubId, None, "HUB", h, hub_info)
                    devices = await self.GetFromCacheOrApi(f"hubs/{hubId}/devices")
                    if devices:
                        for d in devices:
                            device = await self.GetFromCacheOrApi(
                                f"hubs/{hubId}/devices/{d['id']}"
                            )
                            self.create_device(hubId, HubAjax, "DEVICE", d, device)

                    groups = await self.GetFromCacheOrApi(f"hubs/{hubId}/groups")
                    if groups:
                        for g in groups:
                            self.create_device(hubId, HubAjax, "GROUP", g, {})

                    HubAjax.rooms = await self.GetFromCacheOrApi(f"hubs/{hubId}/rooms")

        await self._hass.config_entries.async_forward_entry_setups(
            self.config_entry, PLATFORMS
        )

    async def Subscribe(self, hass):
        @callback
        async def message_received(msg):
            await self.parse_mqtt_message(msg.topic, msg.payload)

        await mqtt.async_subscribe(hass, "jeedom/#", message_received)

    # index  - basic config from index request
    # config = full details
    def create_device(self, parentHubId, HaHubDevice, devicetype, index, config):
        device_registry = dr.async_get(self._hass)

        if devicetype == "DEVICE":
            fw = config["firmwareVersion"]
            hw = config["color"]
            name = config["deviceName"]
            model = config["deviceType"]
        elif devicetype == "HUB":
            fw = config["firmware"]["version"]
            hw = ""
            name = config["name"]
            model = config["hubSubtype"]
        elif devicetype == "GROUP":
            config = index
            name = config["groupName"]
            model = "Group"
            fw = ""
            hw = ""
        else:
            name = "Error"
            model = "Error"
            fw = ""
            hw = ""

        device = device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            connections={(config["id"], DOMAIN)},
            identifiers={(config["id"], DOMAIN)},
            manufacturer=self.manufacturer,
            name=name,
            model=model,
            serial_number=config["id"],
            sw_version=fw,
            hw_version=hw,
        )

        ad = AjaxDevice(self, name, parentHubId, HaHubDevice, devicetype, index, config)
        self.devices[config["id"]] = ad

        Common = [
            "state",
            "masked",
            "online",
            "temperature",
            "signalLevel",
            "nightModeArm",
            "batteryChargeLevelPercentage",
            "tampered",
            "externalPower",
            "externallyPowered",
        ]
        Doors = ["reedClosed", "extraContactClosed"]
        Relays = [
            "switchState",
            "powerConsumedWattsPerHour",
            "currentMilliAmpers",
            "voltageVolts",
            "voltageMilliVolts",
        ]
        Other = ["leakDetected"]

        Sesnors = [Common, Doors, Relays, Other]
        for s in Sesnors:
            for p in s:
                if p in config:
                    if devicetype in ["HUB", "GROUP"] and p == "state":
                        pass
                    else:
                        if p == "batteryChargeLevelPercentage":
                            ad.EnableSensor(
                                "batteryCharge", "batteryChargeLevelPercentage"
                            )
                        else:
                            ad.EnableSensor(p)

        """'
        if 'battery' in d['status']:
            ad.register_api_sensors(['batteryCharge', 'batteryChargeVolt'])
            ad.set_init_value('batteryCharge', d['status']['battery'])
        """

        if model in SWITCH_ENABLED:
            ad.EnableSensor("realState", "switchState")

        if model in ["WallSwitch", "Socket"]:
            ad.EnableSensor("powerWtH", "powerConsumedWattsPerHour")
            ad.EnableSensor("currentMA", "currentMilliAmpers")
            ad.EnableSensor("voltage", "voltageVolts")

        if devicetype == "GROUP":
            ad.EnableSensor("armed", "state")
            ad.EnableSensor("state", "state")

        if devicetype == "HUB":
            ad.EnableSensor("batteryCharge", "battery::chargeLevelPercentage")
            ad.EnableSensor("wifi_level", "wifi::signalLevel")
            ad.EnableSensor("gsmNetworkStatus", "gsm::networkStatus")
            ad.EnableSensor("simCardState", "gsm::simCardState")
            ad.EnableSensor("hub_state", "state")
            ad.EnableSensor("night_mode_armed", "state")
            ad.EnableSensor("night_mode_state", "state")

            ad.AddVirtualSensors(AjaxHubEventSensors)

        ad.RegisterActions()

        return ad

    # Direct API results parsing
    async def on_raw_event(self, payload):
        p = json.loads(payload)
        LOGGER.debug(f"AjaxEvent: {json.dumps(p['data'])}")

        for j in p["data"]:
            m = parse_raw_message(j)
            # self.ajax_user_id = m['user_id']

            #if self.hub_id != m['hub_id']:
            #    # skip messages for other hub
            #    # LOGGER.debug(f"Skip message for other hub {self.hub_id}  {m['hub_id']}")
            #    return

            if m["event"]:
                LOGGER.debug(f"update: {json.dumps(m["event"])}")

                if m["event"]["eventType"] == "SECURITY":
                    if self.enable_ha_user_replace:
                        # If Apply HA Multiuser Hack to event text. Replace Ajax UserName to HA User Name
                        time_since_last_action = (time.time()-self._ha_lastaction_time)
                        if time_since_last_action<7 and self._ha_lastaction_user:
                            ajax_user_name = m['event']['sourceObj']
                            replace_user_name = self._ha_lastaction_user
                            LOGGER.info(f"{time_since_last_action} sec from last Action. AjaxUser->HaUser {ajax_user_name}->{replace_user_name}")
                            for i, u in enumerate(m["updates"]):
                                if u['name']=='eventSecurity':
                                    m["updates"][i]['state']=u['state'].replace(m['event']['sourceObj'], replace_user_name)
                                    break


                    # s=m['event']
                    # prefix   ='!! ' if s['arming_state'] == 'ArmAttepmt' else ''
                    # postfix  =f" | {s['malfunctions']}"  if s['malfunctions'] else ''
                    # print(f"{prefix}{s['human_text']} by {s['user']}{postfix}")

            if m["updates"]:
                for u in m["updates"]:
                    if u["id"] in self.devices:
                        LOGGER.debug(f"update: {json.dumps(u)}")
                        ad = self.devices[u["id"]]
                        await ad.update_param_from_raw_api_mqtt_message(u)
                    else:
                        LOGGER.error(f"Device Not Found {u['id']}. Payload: {payload}")

    async def parse_mqtt_message(self, topic, payload):
        # jeedom/cmd/event/576
        # jeedom/state online
        # jeedom/raw/event
        try:
            if topic == "jeedom/state":
                pass
            elif topic.startswith("jeedom/raw/event"):
                await self.on_raw_event(payload)
            elif topic.startswith("jeedom/cmd/event/"):
                pass
                # await self.on_jeedom_event(topic, payload)
            elif topic.startswith("jeedom/eqLogic/battery/"):
                pass
            else:
                LOGGER.info(
                    f"parse_mqtt_message: unsupported topic {topic} and payload {payload}"
                )

        except:
            LOGGER.error(
                f"Exception in parse_mqtt_message: topic {topic} and payload {payload}"
            )

    async def Apply_HubState_ToGroups(self, hubState):
        LOGGER.debug(f"Groups State changed to hubState: {hubState}")

        for id, d in self.devices.items():
            if d.devicetype == "GROUP":
                v = d.get_sensor_value("state")
                if hubState in [STATE_ARMED, STATE_ARMED_WITH_ERRORS]:
                    if v not in [STATE_ARMED, STATE_ARMED_WITH_ERRORS]:
                        d.SensorsValues["state"] = hubState
                        d.SensorsValues["armed"] = True
                elif hubState == STATE_DISARMED:
                    d.SensorsValues["state"] = STATE_DISARMED
                    d.SensorsValues["armed"] = False
                elif hubState == STATE_ARMATTEMPT:
                    d.SensorsValues["state"] = STATE_DISARMED
                    d.SensorsValues["armed"] = False
                else:
                    pass

                await d.publish_updates("state")
                await d.publish_updates("armed")

    def Calc_HubState_FromGroups(self):
        armed = 0
        total = 0

        for id, d in self.devices.items():
            if d.devicetype == "GROUP":
                v = d.get_sensor_value("armed")
                total = total + 1
                if v:
                    armed = armed + 1

        if total > 0:
            if armed == total:
                return STATE_ARMED
            elif armed == 0:
                return STATE_DISARMED
            else:
                return STATE_HUB_PARTIALLY_ARMED
        else:
            return False

    @property
    def hub_id(self) -> str:
        """ID for dummy hub."""
        # print(f"hub_id {self._id}")
        return self._id

    async def test_connection(self) -> bool:
        """Test connectivity to the Dummy hub is OK."""
        await asyncio.sleep(1)
        # print("test_connection")

        return True


class AjaxDevice:
    details = False

    def __init__(
        self, ha_Hub: AjaxHub, name, parentHubId, parentHub, devicetype, index, config
    ) -> None:
        self.name = name
        self.ha_Hub = ha_Hub
        self.parentHubId = parentHubId
        self.parentHub = parentHub
        self.devicetype = devicetype
        self.config = config
        self.index = index

        self.id = config["id"]

        self.Actions = {}
        self.Switches = {}
        self.SensorsVisible = {}
        self.SensorsValues = {}
        self.sensor_name_callbacks = {}
        self.last_arm_cmd = False

    def parse_sensor_value(self, sensor_name, value, update_type):
        try:
            if update_type == "HUB":
                Code2Label = {
                    "wifi_level": ["NO_SIGNAL", "WEAK", "NORMAL", "STRONG"],
                    "gsmNetworkStatus": ["UNKNOWN", "GSM", "2G", "3G", "4G", "5G"],
                    "simCardState": [
                        "OK",
                        "MISSING",
                        "MALFUNCTION",
                        "LOCKED",
                        "UNKNOWN",
                    ],
                }

                if sensor_name in Code2Label:
                    if value < len(Code2Label[sensor_name]):
                        value = Code2Label[sensor_name][value]

            elif update_type == "GROUP":
                if sensor_name == "armed":
                    value = value == 1
                if sensor_name == "state":
                    value = "Armed" if value == 1 else "Disarmed"

            if self.devicetype == "DEVICE":
                if (self.config["deviceType"] in SWITCH_ENABLED) and (
                    sensor_name == "realState"
                ):
                    if str(value) == "-128":
                        value = False
                    elif str(value) == "0":
                        value = True
        except:
            pass

        return value

    def update_sensor_value(self, sensor_name, update):
        if sensor_name in self.SensorsVisible:
            value = self.parse_sensor_value(
                sensor_name, update["state"], update["type"]
            )
            self.SensorsValues[sensor_name] = value
            return True
        else:
            return False

    def get_path_for_actions(self):
        path = f"/user/{self.ha_Hub.ajax_user_id}/hubs/{self.parentHubId}"

        if self.devicetype == "HUB":
            return path
        elif self.devicetype == "GROUP":
            return f"{path}/groups/{self.id}"
        elif self.devicetype == "DEVICE":
            return f"{path}/devices/{self.id}"
        else:
            return ''

    def Generate_MUTE_FIRE_DETECTORS_config(self):
        return {
            "path": self.get_path_for_actions() + "/commands/muteFireDetectors",
            "data": {"muteType": "ALL_FIRE_DETECTORS"},
            "call_method": "PUT",
        }

    def Generate_PANIC_config(self):
        return {
            "path": self.get_path_for_actions() + "/commands/panic",
            "data": {
                "location": {
                    "latitude": 0,
                    "longitude": 0,
                    "accuracy": 0,
                    "speed": 0,
                    "timestamp": 0,
                }
            },
            "call_method": "PUT",
        }

    def Generate_ARM_config(self, command, ignoreProblems):
        return {
            "path": self.get_path_for_actions() + "/commands/arming",
            "data": {"command": command, "ignoreProblems": ignoreProblems},
            "call_method": "PUT",
        }

    def Generate_Device_config(self, command):
        # CONNECTION_TEST_START, CONNECTION_TEST_STOP,
        # DETECTION_TEST_START, DETECTION_TEST_STOP,
        # MUTE,
        # SWITCH_ON, SWITCH_OFF,
        # SOUND_TEST_START,
        # UNLOCK_DEVICE,
        # DEVICE_SWITCH_STATE,
        # FIRE_SENSOR_TEST,
        # MOTION_OUTDOOR_DETECTION_TEST_START, MOTION_OUTDOOR_UPPER_MOTION_SENSOR_DETECTION_TEST_START, MOTION_OUTDOOR_LOWER_MOTION_SENSOR_DETECTION_TEST_START, MOTION_OUTDOOR_ANTIMASKING_MOTION_SENSOR_DETECTION_TEST_START,
        # MULTI_TRANSMITTER_POWER_RESET,
        # DISABLE_BYPASS, ENABLE_ENGINEER_BYPASS, ENABLE_TAMPER_BYPASS, DISABLE_DEVICE_ONETIME_BYPASS, ENABLE_WHOLE_DEVICE_ONETIME_BYPASS, ENABLE_TAMPER_DEVICE_ONETIME_BYPASS,
        # RESET_PASSWORD, RESET_FORCE_DISARM_PASSWORD,
        # MAKE_PHOTO,
        # UNREGISTERED_FIBRA_DEVICE_BLINK_START, UNREGISTERED_FIBRA_DEVICE_BLINK_STOP,
        # START_CALIBRATION, STOP_CALIBRATION,
        # BUS_POWER_ON, BUS_POWER_OFF,
        # IWH_TEST_START, IWH_TEST_STOP,
        # SELF_TEST,
        # BRIGHTNESS
        return {
            "path": self.get_path_for_actions() + "/command",
            "data": {"command": command, "deviceType": self.config["deviceType"]},
            "call_method": "POST",
        }

    def RegisterActions(self):
        if self.devicetype in ["HUB", "GROUP"]:
            self.RegisterAction("ARM", self.Generate_ARM_config("ARM", False))
            self.RegisterAction("FORCE ARM", self.Generate_ARM_config("ARM", True))
            self.RegisterAction("DISARM", self.Generate_ARM_config("DISARM", True))
            if self.devicetype in ["GROUP"]:
                self.RegisterSwitch("Arm", "ARM", "DISARM", "armed")
                self.RegisterSwitch("Force Arm", "FORCE ARM", "DISARM", "armed")

            if self.devicetype == "HUB":
                self.RegisterAction(
                    "NIGHT_MODE_ON", self.Generate_ARM_config("NIGHT_MODE_ON", False)
                )
                self.RegisterAction(
                    "FORCE_NIGHT_MODE_ON",
                    self.Generate_ARM_config("NIGHT_MODE_ON", True),
                )
                self.RegisterAction(
                    "NIGHT_MODE_OFF", self.Generate_ARM_config("NIGHT_MODE_OFF", True)
                )

                self.RegisterSwitch(
                    "Night Mode", "NIGHT_MODE_ON", "NIGHT_MODE_OFF", "night_mode_armed"
                )
                self.RegisterSwitch(
                    "Force Night Mode",
                    "FORCE_NIGHT_MODE_ON",
                    "NIGHT_MODE_OFF",
                    "night_mode_armed",
                )

                self.RegisterAction(
                    "muteFireDetectors", self.Generate_MUTE_FIRE_DETECTORS_config()
                )
                self.RegisterAction("PANIC", self.Generate_PANIC_config())
        elif self.devicetype in ["DEVICE"]:
            if self.config["deviceType"] in SWITCH_ENABLED:
                self.RegisterAction(
                    "SWITCH_ON", self.Generate_Device_config("SWITCH_ON")
                )
                self.RegisterAction(
                    "SWITCH_OFF", self.Generate_Device_config("SWITCH_OFF")
                )
                self.RegisterSwitch("Enable", "SWITCH_ON", "SWITCH_OFF", "realState")

    def RegisterSwitch(self, name, on, off, state):
        self.Switches[name] = {"on": on, "off": off, "state_sensor_name": state}

    def RegisterAction(self, name, command):
        self.Actions[name] = command

    def AddVirtualSensors(self, sensors):
        for s in sensors:
            self.SensorsVisible[s] = {"json_path": None}
            self.SensorsValues[s] = None

    def ValueFromJson(self, json_path):
        path = json_path.split("::")
        value = self.config
        for p in path:
            if p in value:
                value = value[p]
            else:
                return None

        return value

    def UpdateSensorFromJson(self, sensor_name):
        si = self.SensorsVisible[sensor_name]
        if si["json_path"]:
            v = self.ValueFromJson(si["json_path"])
            if sensor_name == "realState" and si["json_path"] == "switchState":
                # SWITCHED_ON, SWITCHED_OFF, OFF_TOO_LOW_VOLTAGE, OFF_HIGH_VOLTAGE, OFF_HIGH_CURRENT, OFF_SHORT_CIRCUIT, CONTACT_HANG, OFF_HIGH_TEMPERATURE
                v = "SWITCHED_ON" in v
            elif self.devicetype == "HUB" and si["json_path"] == "state":
                '''
                test=[
                        'DISARMED', 'ARMED', 'NIGHT_MODE',
                        'ARMED_NIGHT_MODE_ON', 'ARMED_NIGHT_MODE_OFF', 'DISARMED_NIGHT_MODE_ON', 'DISARMED_NIGHT_MODE_OFF',
                        'PARTIALLY_ARMED_NIGHT_MODE_ON', 'PARTIALLY_ARMED_NIGHT_MODE_OFF']
                '''
                x = v.split("_NIGHT_MODE_")
                night_mode_armed = False
                hub_state = None

                if len(x) == 1:
                    night_mode_armed = v == "NIGHT_MODE"
                    hub_state = v
                elif len(x) == 2:
                    hub_state = x[0]
                    night_mode_armed = x[1] == "ON"

                if sensor_name == "hub_state":
                    v = HubStateToLowerCaseState(hub_state)
                if sensor_name == "night_mode_state":
                    v = "Armed" if night_mode_armed else "Disarmed"
                if sensor_name == "night_mode_armed":
                    v = night_mode_armed
            elif self.devicetype == "GROUP" and sensor_name in ["armed", "state"]:
                if sensor_name == "armed":
                    v = v == "ARMED"
                if sensor_name == "state":
                    v = HubStateToLowerCaseState(v)

            self.SensorsValues[sensor_name] = v
        else:
            self.SensorsValues[sensor_name] = self.config[sensor_name]

    def EnableSensor(self, sensor_name, json_path=None):
        self.SensorsVisible[sensor_name] = {"json_path": json_path}
        self.UpdateSensorFromJson(sensor_name)

    def register_sensor(self, sensor_name):
        self.sensor_name_callbacks[sensor_name] = set()

    async def update_param_from_raw_api_mqtt_message(self, u):
        sensor_name = SensorNameFromLogToConfig(u)

        # unsupported sesnor
        if sensor_name == False:
            LOGGER.debug(f"Ignored: {json.dumps(u)}")
            return

        hubState = False
        updateGroupsStateFromHubState = False

        # Parse HUB state update and apply it to ALL groups. Update mqtt message
        if u["type"] == "HUB" and u["name"] == "state":
            if (u["state"] in [0, 1]):
                hubState = STATE_ARMED if u["state"] == 1 else STATE_DISARMED

                if not self.ha_Hub.enable_apply_hub_state_to_groups:
                    LOGGER.debug(f"Skip Hub State {hubState}. HUB.state Message")
                    return

                updateGroupsStateFromHubState = hubState
                LOGGER.debug(f"Apply Hub State {updateGroupsStateFromHubState} to All Groups. HUB.state Message")

                # State from UPDATE message overrides Extended status from SECURITY event
                if (
                    self.SensorsValues["hub_state"] == STATE_ARMED_WITH_ERRORS
                    and u["state"] == 1
                ):
                    hubState = False

        # GROUP state 0 or 1 come from update mqtt
        # GROUP.armed should be updated
        # GROUP.state should be updated
        elif u["type"] == "GROUP" and u["name"] == "state":
            # update group.armed sensor
            if self.update_sensor_value(sensor_name, u):
                LOGGER.debug("Group state Updated")
                await self.publish_updates(sensor_name)

            # update group.sensor. State from UPDATE message overrides Extended status from SECURITY event
            skip_update = (
                self.SensorsValues["state"] == STATE_ARMED_WITH_ERRORS
                and u["state"] == 1
            )
            if not skip_update:
                if self.update_sensor_value("state", u):
                    LOGGER.debug("Group state Updated")
                    await self.publish_updates("state")

            hubState = self.ha_Hub.Calc_HubState_FromGroups()
            LOGGER.debug(f"Hub state calculated from groups: {hubState}")

        # Notify HUB to update hub_state sensor and verify PARTIALLY_ARMED state
        # this come from event mqtt message
        elif u["type"] == "SECURITY_EVENT_PARSED" and u["name"] == "hub_state":
            if u["state"] in [STATE_ARMED, STATE_DISARMED]:
                updateGroupsStateFromHubState = u["state"]
                LOGGER.debug(f"Apply Hub State {updateGroupsStateFromHubState} to All Groups. From Parsed Event")
            elif u["state"] == STATE_HUB_CHECK_GROUPS:
                hubState = self.ha_Hub.Calc_HubState_FromGroups()
                LOGGER.debug(f"Calculated Hub State {hubState} from Groups. From Parsed Event")

        if hubState or updateGroupsStateFromHubState:
            if hubState:
                hub = self.parentHub if self.devicetype != "HUB" else self
                hub.SensorsValues["hub_state"] = hubState
                LOGGER.debug(f"Hub State changed to {hubState}")
                await hub.publish_updates("hub_state")

            if updateGroupsStateFromHubState:
                await self.ha_Hub.Apply_HubState_ToGroups(hubState)

            return

        if self.update_sensor_value(sensor_name, u):
            await self.publish_updates(sensor_name)
        else:
            t = f"Unparsed PARAM: {self.devicetype}: {self.name}:{u['name']} => {u['state']} | {u['type']}"
            LOGGER.error(t)

    def get_sensor_value(self, sensor_name):
        if sensor_name in self.SensorsValues:
            return self.SensorsValues[sensor_name]
        else:
            if sensor_name not in self.Actions:
                LOGGER.info(f"Error reading {self.name}.{sensor_name}")
                return None

    def get_switch_is_on(self, sensor_name):
        sw = self.Switches[sensor_name]
        return self.SensorsValues[sw["state_sensor_name"]]

    def register_callback(self, sensor_name, callback: Callable[[], None]) -> None:
        self.sensor_name_callbacks[sensor_name].add(callback)

    def remove_callback(self, sensor_name, callback: Callable[[], None]) -> None:
        self.sensor_name_callbacks[sensor_name].discard(callback)

    # In a real implementation, this library would call it's call backs when it was
    # notified of any state changeds for the relevant device.
    async def publish_updates(self, sensor_name) -> None:
        """Schedule call all registered callbacks."""
        for callback in self.sensor_name_callbacks[sensor_name]:
            callback()

    # In a real implementation, this library would call it's call backs when it was
    # notified of any state changeds for the relevant device.
    def get_state_sensor_for_command(self, cmd):
        if "command" in cmd["data"]:
            command = cmd["data"]["command"]

            if command in ["NIGHT_MODE_ON", "NIGHT_MODE_OFF"]:
                return "night_mode_state"
            elif command in ["ARM", "DISARM"]:
                if self.devicetype == "HUB":
                    return "hub_state"
                else:
                    return "state"

        return None

    @callback
    async def check_if_request_is_expired(self, *_: datetime) -> None:
        if self.last_arm_cmd:
            state_sensor = self.last_arm_cmd['state_sensor']
            if self.SensorsValues[state_sensor]==STATE_EXEC_CMD:
                prev_state = self.last_arm_cmd['prev_state']
                LOGGER.info(f"No HUB Answer. State for {self.name} returned to {prev_state}")
                self.SensorsValues[state_sensor] = prev_state
                await self.publish_updates(state_sensor)
                self.last_arm_cmd = False

    async def exec_command(self, cmd_name, context=None) -> None:
        if (not self.ha_Hub.enable_panic_button) and (cmd_name == "PANIC"):
            raise ServiceValidationError("Panic button is Disabled in Settings")

        if cmd_name in self.Actions:
            cmd = self.Actions[cmd_name]

            await self.ha_Hub.setContextFromLastCall(context)

            # update state sensor for ARM/DISARM commands
            state_sensor = self.get_state_sensor_for_command(cmd)
            if state_sensor:
                self.last_arm_cmd = {
                    'prev_state'    : self.SensorsValues[state_sensor],
                    'state_sensor'  : state_sensor
                }

                self.SensorsValues[state_sensor] = STATE_EXEC_CMD
                await self.publish_updates(state_sensor)

                expiration_at = utcnow() + timedelta(seconds=10)
                async_track_point_in_utc_time(self.ha_Hub._hass, self.check_if_request_is_expired, expiration_at)

            if self.ha_Hub.replace_api_addr_before_call:
                self.ha_Hub.ajax_api.adrss = self.ha_Hub.replace_api_addr_before_call

            LOGGER.debug(f"ajax_api.exec_cmd: {json.dumps(cmd)}")

            r = await self.ha_Hub.ajax_api.exec_cmd(cmd["path"], cmd["data"], cmd["call_method"])

            LOGGER.debug(f"ajax_api.exec_cmd return {json.dumps(r)}, LastError: {self.ha_Hub.ajax_api.last_exec_error}")

            # r can be ''
            if r == False:
                LOGGER.error(f"ajax_api.exec_cmd errors: {self.ha_Hub.ajax_api.last_exec_error}")
                raise ServiceValidationError(self.ha_Hub.ajax_api.last_exec_error)

            #if state_sensor:
            #    if not await self.wait_for_request_response_message(state_sensor):
            #        self.SensorsValues[state_sensor] = STATE_EXEC_CMD
            #        await self.publish_updates(state_sensor)

            return r

        return None

    @property
    def online(self) -> bool:
        if "online" in self.config:
            return self.config["online"]
        else:
            return True
