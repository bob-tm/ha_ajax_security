"""Hun Integration for Ajax Security."""

from __future__ import annotations

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
from homeassistant.util import Callable, utcnow

from .ajax_devices_schema import (
    SWITCH_ENABLED,
    EnableSensorsByDeviceType,
    EnableSensorsByModel,
    Enums_by_sensor_name,
    TryForAllSensors,
)
from .const import (
    CONF_API_URL,
    CONF_APPLY_HUB_STATE_TO_GROUPS,
    CONF_AUTH_TOKEN,
    CONF_BASE_URL,
    CONF_PANIC_BUTTON,
    CONF_REPLACE_USERNAME,
    DOMAIN,
    LOGGER,
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
    """Used on setup."""
    try:
        japi = JeedomAjaxApi(host.rstrip("\\"), CONF_API_URL, token)
        return await japi.isOk()
    except:  # noqa: E722
        return False


class AjaxHub:
    """HA Main Hub."""
    manufacturer = "Ajax"

    def __init__(self, hass: HomeAssistant, entry_data, config_entry) -> None:
        """Init from config."""
        self.disk_cache = CACHE_AJAX_REQUESTS
        self._apikey    = entry_data[CONF_AUTH_TOKEN]
        self._host      = entry_data[CONF_BASE_URL].rstrip("\\")
        self._apiurl    = CONF_API_URL

        self.hass  = hass
        self._name  = self._host
        self._id    = self._host.lower()
        self.hubs   = {}

        self.enable_panic_button                = False
        self.enable_ha_user_replace             = True
        self.enable_apply_hub_state_to_groups   = False
        self.applyOptions(config_entry.options)

        self.replace_api_addr_before_call = False
        # debug feature to test bad url for testing
        # self.replace_api_addr_before_call = "https://google.com/sdf"

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
        os.makedirs(self.cache_folder, exist_ok=True)  # noqa: PTH103

    def applyOptions(self, options):
        """Apply options at startup or after options flow."""
        self.enable_panic_button = options.get(CONF_PANIC_BUTTON, self.enable_panic_button)
        self.enable_ha_user_replace = options.get(CONF_REPLACE_USERNAME, self.enable_ha_user_replace)
        self.enable_apply_hub_state_to_groups = options.get(CONF_APPLY_HUB_STATE_TO_GROUPS, self.enable_apply_hub_state_to_groups)

    async def getUserNameByIdFromAuth(self, user_id):
        '''Get UserName by user_id.'''
        users = await self.hass.auth.async_get_users()
        for user in users:
            if user_id==user.id:
                return user.name
        return None

    def getUserNameByIdFromPersonSync(self, user_id):
        '''Get UserName by user_id from Person.'''
        persons = self.hass.states.all("person")
        for p in persons:
            if user_id == p.attributes["user_id"]:
                return p.name
        return None

    async def getUserNameByIdFromPerson(self, user_id):
        '''Get UserName by user_id.'''
        return await self.hass.async_add_executor_job(self.getUserNameByIdFromPersonSync, user_id)

    async def getUserNameById(self, user_id):
        user1 = await self.getUserNameByIdFromAuth(user_id)
        user2 = await self.getUserNameByIdFromPerson(user_id)
        #print(user1, user2)
        LOGGER.debug(f"Detected {user1} and {user2}")
        if user1: return user1
        if user2: return user2

        return None

    async def setUserNameFromId(self, user_id):
        """Convert userid from context to person name."""
        user = await self.getUserNameById(user_id)
        LOGGER.debug(f"Action by {user} with id {user_id}")
        if user is not None:
            self._ha_lastaction_user = user
            self._ha_lastaction_time = time.time()
            return

        self._ha_lastaction_user = None
        self._ha_lastaction_time = 0

    async def setContextFromLastCall(self, context):
        """Save user_id who make an arm/disarm action."""
        await self.setUserNameFromId(context.user_id)

    async def getCachedJsonFile(self, filename: str) -> dict | None:
        """Get Json From Disk."""
        def getCachedJsonFileBlocking():
            if not self.disk_cache:
                return False

            fn = self.cache_folder + os.sep + filename
            if not os.path.exists(fn):  # noqa: PTH110
                return False

            with open(fn) as json_data:  # noqa: PTH123
                return json.load(json_data)

        return await self.hass.async_add_executor_job(getCachedJsonFileBlocking) # type: ignore

    def saveJsonToCache(self, filename, data):
        """Save JSON to disk."""
        # if not self.disk_cache:
        #    return False

        fn = self.cache_folder + os.sep + filename
        path = Path(fn)
        os.makedirs(path.parent.absolute(), exist_ok=True)

        json_str = json.dumps(data, indent=4)
        with open(fn, "w") as f:
            f.write(json_str)

    async def GetFromCacheOrApi(self, path):
        """Check saved JSON or call API."""
        file_cache = f"{self.ajax_user_id}/{path}.json"
        r = await self.getCachedJsonFile(file_cache)
        if not r:
            r = await self.ajax_api.get_config_json(path)
            if r:
                self.saveJsonToCache(file_cache, r)

        return r

    async def GetUserIdFromCacheOrApi(self):
        """Get AjaxApi User ID."""
        file_cache = "userid.json"
        r = await self.getCachedJsonFile(file_cache)
        if not r:
            r = {}
            r["userid"] = await self.ajax_api.get_userId()
            if r:
                self.saveJsonToCache(file_cache, r)

        return r["userid"]

    async def LoadTestConfig(self):
        """Load test config from test forlder with hub_id=test."""
        self.ajax_user_id = "test"
        from os import listdir
        from os.path import isfile, join

        mypath = self.cache_folder + os.sep + "/devices/"
        onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

        hub_json = await self.getCachedJsonFile("hub.json")
        if not hub_json:
            return

        hub_json["id"] = "test"
        hubId = "test"
        self.hubs[hubId] = {"hubAjax": None, "devices": {}, "rooms":{} }
        HubAjax = self.create_device(hubId, None, "HUB", {}, hub_json)
        self.hubs[hubId]["hubAjax"] = HubAjax

        for f in onlyfiles:
            device = await self.getCachedJsonFile("/devices/" + f)
            self.create_device(hubId, HubAjax, "DEVICE", {}, device)

    async def LoadAjaxDevices(self):
        """Create API and Load main config."""
        if (self._host == "test") and (self._apikey == "test"):
            await self.LoadTestConfig()
            return

        self.ajax_api = JeedomAjaxApi(self._host, self._apiurl, self._apikey)
        self.ajax_user_id = await self.GetUserIdFromCacheOrApi()
        if not self.ajax_user_id:
            LOGGER.error("Can not get Ajax UserId: Check if Patch is applied and ajax token is correct")
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
                    self.hubs[hubId] = {"hubAjax": None, "devices": {}, "rooms": {}}
                    HubAjax = self.create_device(hubId, None, "HUB", h, hub_info)
                    self.hubs[hubId]["hubAjax"] = HubAjax

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

                    self.hubs[hubId]["rooms"] = await self.GetFromCacheOrApi(f"hubs/{hubId}/rooms")

    async def Subscribe(self, hass):
        """Start receiving mqtt messages."""
        @callback
        async def message_received(msg):
            await self.parse_mqtt_message(msg.topic, msg.payload)

        await mqtt.async_subscribe(hass, "jeedom/#", message_received)

    # index  - basic config from index request
    # config = full details
    def create_device(self, parentHubId, HaHubDevice, devicetype, index, config):
        """Create AjaxDevice from JSON config."""

        device_registry = dr.async_get(self.hass)

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

        device_registry.async_get_or_create(
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
        self.hubs[parentHubId]["devices"][config["id"]] = ad

        for s in TryForAllSensors:
            for p in s:
                if p in config:
                    if devicetype in ["HUB", "GROUP"] and p == "state":
                        pass
                    elif p == "batteryChargeLevelPercentage":
                        ad.EnableSensor("batteryCharge", "batteryChargeLevelPercentage")
                    else:
                        ad.EnableSensor(p)

        for conf in EnableSensorsByModel:
            if model in conf['model']:
                for p in conf['params']:
                    ad.EnableSensor(p[0], p[1])

        #if model in SWITCH_ENABLED:
        #    ad.EnableSensor("realState", "switchState")

        #if model in ["WallSwitch", "Socket"]:
        #    ad.EnableSensor("powerWtH", "powerConsumedWattsPerHour")
        #    ad.EnableSensor("currentMA", "currentMilliAmpers")
        #    ad.EnableSensor("voltage", "voltageVolts")

        #if model in ["Transmitter"]:
        #    ad.EnableSensor("externalContactOK", "externalContactTriggered")
        #    ad.EnableSensor("isBypassed", "")
        #    ad.EnableSensor("bypassMode", "bypassState")
        #    # ENGINEER_BYPASS_ACTIVE, TAMPER_BYPASS_ACTIVE, AUTO_BYPASSED_BY_ALARMS_COUNT, AUTO_BYPASSED_AS_NOT_RESTORED, ONETIME_FULL_BYPASS_ENABLED, ONETIME_TAMPER_BYPASS_ENABLED

        for conf in EnableSensorsByDeviceType:
            if devicetype in conf['type']:
                for p in conf['params']:
                    ad.EnableSensor(p[0], p[1])

        #if devicetype == "GROUP":
        #    ad.EnableSensor("armed", "state")
        #    ad.EnableSensor("state", "state")

        #if devicetype == "HUB":
        #    ad.EnableSensor("batteryCharge", "battery::chargeLevelPercentage")
        #    ad.EnableSensor("wifi_level", "wifi::signalLevel")
        #    ad.EnableSensor("gsmNetworkStatus", "gsm::networkStatus")
        #    ad.EnableSensor("simCardState", "gsm::simCardState")
        #    ad.EnableSensor("hub_state", "state")
        #    ad.EnableSensor("night_mode_armed", "state")
        #    ad.EnableSensor("night_mode_state", "state")

        if devicetype == "HUB":
            ad.AddVirtualSensors(AjaxHubEventSensors)

        ad.RegisterActions()

        return ad

    # Direct API results parsing
    async def on_raw_event(self, payload):
        """Parse Messages from Ajax API."""
        p = json.loads(payload)
        LOGGER.debug(f"AjaxEvent: {json.dumps(p['data'])}")

        for j in p["data"]:
            m = parse_raw_message(j)
            # self.ajax_user_id = m['user_id']

            hub_id = m["hub_id"]

            # hacks for testing
            if hub_id in ["hub_id"]:
                hub_id = "test"

            if hub_id in self.hubs:
                hub = self.hubs[hub_id]
            else:
                # skip messages for other hub
                # LOGGER.debug(f"Skip message for other hub {self.hub_id}  {m['hub_id']}")
                return

            if m["event"]:
                LOGGER.debug(f"update: {json.dumps(m['event'])}")

                if m["event"]["eventType"] == "SECURITY":
                    if self.enable_ha_user_replace:
                        # If Apply HA Multiuser Hack to event text. Replace Ajax UserName to HA User Name
                        time_since_last_action = time.time() - self._ha_lastaction_time
                        if time_since_last_action < 7 and self._ha_lastaction_user:
                            ajax_user_name = m["event"]["sourceObj"]
                            replace_user_name = self._ha_lastaction_user
                            LOGGER.info(
                                f"{time_since_last_action} sec from last Action. AjaxUser->HaUser {ajax_user_name}->{replace_user_name}"
                            )
                            for i, u in enumerate(m["updates"]):
                                if u["name"] == "eventSecurity":
                                    m["updates"][i]["state"] = u["state"].replace(
                                        m["event"]["sourceObj"], replace_user_name
                                    )
                                    break

                    # s=m['event']
                    # prefix   ='!! ' if s['arming_state'] == 'ArmAttepmt' else ''
                    # postfix  =f" | {s['malfunctions']}"  if s['malfunctions'] else ''
                    # print(f"{prefix}{s['human_text']} by {s['user']}{postfix}")

            if m["updates"]:
                for u in m["updates"]:
                    devices = hub["devices"]
                    if u["id"] in devices:
                        LOGGER.debug(f"update: {json.dumps(u)}")
                        ad = devices[u["id"]]
                        await ad.update_param_from_raw_api_mqtt_message(hub, u)
                    else:
                        LOGGER.error(f"Device Not Found {u['id']}. Payload: {payload}")

    async def parse_mqtt_message(self, topic, payload):
        """Check Mqtt Topics."""
        # jeedom/cmd/event/576
        # jeedom/state online
        # jeedom/raw/event
        try:
            if topic.startswith("jeedom/raw/event"):
                await self.on_raw_event(payload)
        except:
            LOGGER.error(f"Exception in parse_mqtt_message: topic {topic} and payload {payload}")

    async def Apply_HubState_ToGroups(self, hub, hubState):
        '''Calculate group states from Hub state.'''

        LOGGER.debug(f"Groups State changed to hubState: {hubState}")

        for d in hub["devices"].values():
            if d.devicetype == "GROUP":
                v = d.get_sensor_value("state")
                if hubState in [STATE_ARMED, STATE_ARMED_WITH_ERRORS]:
                    if v not in [STATE_ARMED, STATE_ARMED_WITH_ERRORS]:
                        d.SensorsValues["state"] = hubState
                        d.SensorsValues["armed"] = True
                elif hubState in (STATE_DISARMED, STATE_ARMATTEMPT):
                    d.SensorsValues["state"] = STATE_DISARMED
                    d.SensorsValues["armed"] = False
                else:
                    pass

                await d.publish_updates("state")
                await d.publish_updates("armed")

    def Calc_HubState_FromGroups(self, hub):
        '''Calc hub state from groups. Return False | STATE_ARMED | STATE_DISARMED | STATE_HUB_PARTIALLY_ARMED.'''

        armed = 0
        total = 0

        for d in hub["devices"].values():
            if d.devicetype == "GROUP":
                v = d.get_sensor_value("armed")
                total = total + 1
                if v:
                    armed = armed + 1

        if total > 0:
            if armed == total:  return STATE_ARMED     # noqa: E701
            if armed == 0:      return STATE_DISARMED  # noqa: E701

            return STATE_HUB_PARTIALLY_ARMED

        return False


class AjaxDevice:
    '''Class for Ajax Device.'''
    details = False

    def __init__(self, ha_Hub: AjaxHub, name, parentHubId, parentHub, devicetype, index, config)->None:
        '''Init Ajax Device for parentHub.'''

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
        self.last_arm_cmd = None

    def parse_sensor_value(self, sensor_name, value, update_type):
        '''Parse sensor value from mqtt message.'''

        try:
            if update_type == "HUB":
                if sensor_name in Enums_by_sensor_name:
                    if value < len(Enums_by_sensor_name[sensor_name]):
                        value = Enums_by_sensor_name[sensor_name][value]

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
        except:  # noqa: E722
            pass

        return value

    def update_sensor_value(self, sensor_name, update):
        '''Check, Parse and update sensor from mqtt message.'''

        if sensor_name in self.SensorsVisible:
            value = self.parse_sensor_value(
                sensor_name, update["state"], update["type"]
            )
            self.SensorsValues[sensor_name] = value
            return True
        else:  # noqa: RET505
            return False

    def get_path_for_actions(self):
        '''Generate command Ajax API path by devicetype.'''

        path = f"/user/{self.ha_Hub.ajax_user_id}/hubs/{self.parentHubId}"

        if self.devicetype == "HUB":
            return path
        elif self.devicetype == "GROUP":
            return f"{path}/groups/{self.id}"
        elif self.devicetype == "DEVICE":
            return f"{path}/devices/{self.id}"
        else:
            return ""

    def Generate_MUTE_FIRE_DETECTORS_config(self):
        '''Ajax API params for Mute.'''
        return {
            "path": self.get_path_for_actions() + "/commands/muteFireDetectors",
            "data": {"muteType": "ALL_FIRE_DETECTORS"},
            "call_method": "PUT",
        }

    def Generate_PANIC_config(self):
        '''Ajax API params for Panic.'''
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
        '''Ajax API params for Arm/Disarm.'''
        return {
            "path": self.get_path_for_actions() + "/commands/arming",
            "data": {"command": command, "ignoreProblems": ignoreProblems},
            "call_method": "PUT",
        }

    def Generate_Device_config(self, command):
        '''Ajax API params for Device.'''
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
        '''Add buttons and switches to HA Device.'''

        if self.devicetype in ["HUB", "GROUP"]:
            self.RegisterAction("ARM", self.Generate_ARM_config("ARM", False))
            self.RegisterAction("FORCE ARM", self.Generate_ARM_config("ARM", True))
            self.RegisterAction("DISARM", self.Generate_ARM_config("DISARM", True))
            if self.devicetype in ["GROUP"]:
                self.RegisterSwitch("Arm", "ARM", "DISARM", "armed")
                self.RegisterSwitch("Force Arm", "FORCE ARM", "DISARM", "armed")

            if self.devicetype == "HUB":
                self.RegisterAction("NIGHT_MODE_ON",        self.Generate_ARM_config("NIGHT_MODE_ON",  False))
                self.RegisterAction("FORCE_NIGHT_MODE_ON",  self.Generate_ARM_config("NIGHT_MODE_ON",  True))
                self.RegisterAction("NIGHT_MODE_OFF",       self.Generate_ARM_config("NIGHT_MODE_OFF", True))
                self.RegisterSwitch("Night Mode",       "NIGHT_MODE_ON",        "NIGHT_MODE_OFF", "night_mode_armed")
                self.RegisterSwitch("Force Night Mode", "FORCE_NIGHT_MODE_ON",  "NIGHT_MODE_OFF", "night_mode_armed")

                self.RegisterAction("muteFireDetectors", self.Generate_MUTE_FIRE_DETECTORS_config())
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
        '''Add switch to internal array.'''
        self.Switches[name] = {"on": on, "off": off, "state_sensor_name": state}

    def RegisterAction(self, name, command):
        '''Add button to internal array.'''
        self.Actions[name] = command

    def AddVirtualSensors(self, sensors):
        '''Add sesnor that do not present in JSON config.'''
        for s in sensors:
            self.SensorsVisible[s] = {"json_path": None}
            self.SensorsValues[s] = None

    def ValueFromJson(self, json_path):
        '''Parse JSON config data to HA sensor value.'''

        if json_path is None:
            return None

        path = json_path.split("::")
        value = self.config
        for p in path:
            if p in value:
                value = value[p]
            else:
                return None

        return value

    def UpdateSensorFromJson(self, sensor_name):
        '''Convert JSON config data to HA sensor value.'''
        si = self.SensorsVisible[sensor_name]

        # sensors not present in json config, only updated by mqtt messages
        if si["json_path"] == "":
            return

        if si["json_path"]:
            v = self.ValueFromJson(si["json_path"])
            if v is None:
                return

            if sensor_name == "realState" and si["json_path"] == "switchState":
                # SWITCHED_ON, SWITCHED_OFF, OFF_TOO_LOW_VOLTAGE, OFF_HIGH_VOLTAGE, OFF_HIGH_CURRENT, OFF_SHORT_CIRCUIT, CONTACT_HANG, OFF_HIGH_TEMPERATURE
                v = "SWITCHED_ON" in v
            elif self.devicetype == "HUB" and si["json_path"] == "state":

                # test=[
                #        'DISARMED', 'ARMED', 'NIGHT_MODE',
                #        'ARMED_NIGHT_MODE_ON', 'ARMED_NIGHT_MODE_OFF', 'DISARMED_NIGHT_MODE_ON', 'DISARMED_NIGHT_MODE_OFF',
                #        'PARTIALLY_ARMED_NIGHT_MODE_ON', 'PARTIALLY_ARMED_NIGHT_MODE_OFF']

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
        '''Add sensor from JSON to HA.'''
        self.SensorsVisible[sensor_name] = {"json_path": json_path}
        self.UpdateSensorFromJson(sensor_name)

    def register_sensor(self, sensor_name):
        '''Create set for callbacks.'''
        self.sensor_name_callbacks[sensor_name] = set()

    async def update_hub_and_group_states(self, sensor_name, hub, u):
        '''Parse HUB and GROUP states. if Return  True - do not continue.'''
        hubState = False
        updateGroupsStateFromHubState = False

        # Parse HUB state update and apply it to ALL groups. Update mqtt message
        if u["type"] == "HUB" and u["name"] == "state":
            if u["state"] in [0, 1]:
                hubState = STATE_ARMED if u["state"] == 1 else STATE_DISARMED

                if not self.ha_Hub.enable_apply_hub_state_to_groups:
                    LOGGER.debug(f"Skip Hub State {hubState}. HUB.state Message")
                    return True

                updateGroupsStateFromHubState = hubState
                LOGGER.debug(
                    f"Apply Hub State {updateGroupsStateFromHubState} to All Groups. HUB.state Message"
                )

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

            hubState = self.ha_Hub.Calc_HubState_FromGroups(hub)
            LOGGER.debug(f"Hub state calculated from groups: {hubState}")

        # Notify HUB to update hub_state sensor and verify PARTIALLY_ARMED state
        # this come from event mqtt message
        elif u["type"] == "SECURITY_EVENT_PARSED" and u["name"] == "hub_state":
            if u["state"] in [STATE_ARMED, STATE_DISARMED]:
                updateGroupsStateFromHubState = u["state"]

                LOGGER.debug(
                    f"Apply Hub State {updateGroupsStateFromHubState} to All Groups. From Parsed Event"
                )
            elif u["state"] == STATE_HUB_CHECK_GROUPS:
                hubState = self.ha_Hub.Calc_HubState_FromGroups(hub)

                LOGGER.debug(
                    f"Calculated Hub State {hubState} from Groups. From Parsed Event"
                )

        if hubState or updateGroupsStateFromHubState:
            if hubState:
                hub = self.parentHub if self.devicetype != "HUB" else self
                hub.SensorsValues["hub_state"] = hubState
                LOGGER.debug(f"Hub State changed to {hubState}")
                await hub.publish_updates("hub_state")

            if updateGroupsStateFromHubState:
                await self.ha_Hub.Apply_HubState_ToGroups(hub, hubState)

            return True

        return False

    async def update_param_from_raw_api_mqtt_message(self, hub, u):
        '''Parse value and update HA sensor.'''
        sensor_name = SensorNameFromLogToConfig(u)

        # unsupported sesnor
        if sensor_name == False:  # noqa: E712
            LOGGER.debug(f"Ignored: {json.dumps(u)}")
            return

        # ARM/Disarm status updates
        if await self.update_hub_and_group_states(sensor_name, hub, u):
            return

        # device online/offline
        if sensor_name == "online":
            if self.update_sensor_value(sensor_name, u):
                await self.UpdateOnlineStatus()
                return

        # everything else
        if self.update_sensor_value(sensor_name, u):
            await self.publish_updates(sensor_name)
        else:
            t = f"Unparsed PARAM: {self.devicetype}: {self.name}:{u['name']} => {u['state']} | {u['type']}"
            LOGGER.error(t)

    def get_sensor_value(self, sensor_name):
        '''Get value.'''
        if sensor_name in self.SensorsValues:
            return self.SensorsValues[sensor_name]

        if sensor_name not in self.Actions:
            LOGGER.info(f"Error reading {self.name}.{sensor_name}")

        return None

    def get_switch_is_on(self, sensor_name):
        '''Is switch is on.'''
        sw = self.Switches[sensor_name]
        return self.SensorsValues[sw["state_sensor_name"]]

    def register_callback(self, sensor_name, call_back: Callable[[], None]) -> None:
        '''Callback add.'''
        self.sensor_name_callbacks[sensor_name].add(call_back)

    def remove_callback(self, sensor_name, call_back: Callable[[], None]) -> None:
        '''Callback remove.'''
        self.sensor_name_callbacks[sensor_name].discard(call_back)

    # notified of any state changeds for the relevant device.
    async def publish_updates(self, sensor_name) -> None:
        """Schedule call all registered callbacks."""
        for call_back in self.sensor_name_callbacks[sensor_name]:
            call_back()

    def get_state_sensor_for_command(self, cmd):
        '''Return None | state | hub_state | night_mode_state.'''
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

    async def check_if_request_is_expired(self, *_: datetime) -> None:
        '''Ajax API does not send any return if ARM already Armed group or Hub. Check such case here.'''
        if self.last_arm_cmd:
            state_sensor = self.last_arm_cmd["state_sensor"]
            if self.SensorsValues[state_sensor] == STATE_EXEC_CMD:
                prev_state = self.last_arm_cmd["prev_state"]
                LOGGER.info(
                    f"No HUB Answer. State for {self.name} returned to {prev_state}"
                )
                self.SensorsValues[state_sensor] = prev_state
                await self.publish_updates(state_sensor)
                self.last_arm_cmd = None

    async def exec_command(self, cmd_name, context=None) -> None:
        '''Run AJAX Api command.'''
        if (not self.ha_Hub.enable_panic_button) and (cmd_name == "PANIC"):
            raise ServiceValidationError("Panic button is Disabled in Settings")

        if cmd_name in self.Actions:
            cmd = self.Actions[cmd_name]

            await self.ha_Hub.setContextFromLastCall(context)

            # update state sensor for ARM/DISARM commands
            state_sensor = self.get_state_sensor_for_command(cmd)
            if state_sensor:
                self.last_arm_cmd = {
                    "prev_state"  : self.SensorsValues[state_sensor],
                    "state_sensor": state_sensor,
                }

                self.SensorsValues[state_sensor] = STATE_EXEC_CMD
                await self.publish_updates(state_sensor)

                expiration_at = utcnow() + timedelta(seconds=10)
                async_track_point_in_utc_time(
                    self.ha_Hub.hass, self.check_if_request_is_expired, expiration_at
                )

            if self.ha_Hub.replace_api_addr_before_call:
                self.ha_Hub.ajax_api.adrss = self.ha_Hub.replace_api_addr_before_call

            LOGGER.debug(f"ajax_api.exec_cmd: {json.dumps(cmd)}")

            r = await self.ha_Hub.ajax_api.exec_cmd(
                cmd["path"], cmd["data"], cmd["call_method"]
            )

            LOGGER.debug(
                f"ajax_api.exec_cmd return {json.dumps(r)}, LastError: {self.ha_Hub.ajax_api.last_exec_error}"
            )

            # r can be '', so only == False
            if r == False:
                LOGGER.error(
                    f"ajax_api.exec_cmd errors: {self.ha_Hub.ajax_api.last_exec_error}"
                )
                raise ServiceValidationError(self.ha_Hub.ajax_api.last_exec_error)

            return r

        return None

    async def UpdateOnlineStatus(self):
        '''Update All Device sensors available status.'''
        t = f"{self.name} online status is {self.online}"
        LOGGER.debug(t)

        # update each entity for device
        for x in self.SensorsVisible:
            await self.publish_updates(x)

        for a in self.Actions:
            await self.publish_updates(a)

    @property
    def online(self) -> bool:
        '''AjaxDevice is online.'''
        if "online" in self.SensorsValues:
            return self.SensorsValues["online"]
        else:
            return True
