'''Ajax sensor rules.'''

BinarySensors = [
    "online",
    "masked",
    "reedClosed",
    "realState",
    "extraContactClosed",
    "tampered",
    "externallyPowered",
    "armed",
    "night_mode_armed",
    "leakDetected",
    "externalContactOK",
]
Diagnostic = [
    "event",
    "eventTag",
    "eventCode",
    "eventTextShort",
    "eventJson",
    "eventMalfunctions",
    "eventArmingState",
    "batteryChargeLevelPercentage",
    "batteryCharge",
    "wifi_level",
    "nightModeArm",
    "switchState",
    "signalLevel",
    "online",
    "gsmNetworkStatus",
    "buzzerState",
    "bypassMode",
    "isBypassed",
]

SWITCH_ENABLED = ["Relay", "WallSwitch", "Socket"]


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

TryForAllSensors = [Common, Doors, Relays, Other]

EnableSensorsByModel= [
        #{
        #    "model" : ["example"],
        #    "params": [
        #        ["HA sensorName",   "JSON path, : as level delimetr"]
        #    ]
        #},
        {
            "model" : ["WallSwitch", "Socket"],
            "params": [
                ["powerWtH",    "powerConsumedWattsPerHour"],
                ["currentMA",   "currentMilliAmpers"],
                ["voltage",     "voltageVolts"]
            ]
        },
        {
            "model" : ["Relay", "WallSwitch", "Socket"],
            "params": [
                ["realState",   "switchState"]
            ]
        },
        {
            "model" : ["Transmitter"],
            "params": [
                ["externalContactOK",   "externalContactTriggered"],
                ["isBypassed",          ""                        ],
                ["bypassMode",          "bypassState"             ]
            ]
        }
]

EnableSensorsByDeviceType=[
        {
            "type"  : "GROUP",
            "params": [
                ["armed",  "state"],
                ["state",  "state"]
            ]
        },
        {
            "type"  : "HUB",
            "params": [
                ["batteryCharge",       "battery::chargeLevelPercentage"],
                ["wifi_level",          "wifi::signalLevel"],
                ["gsmNetworkStatus",    "gsm::networkStatus"],
                ["simCardState",        "gsm::simCardState"],
                ["hub_state",           "state"],
                ["night_mode_armed",    "state"],
                ["night_mode_state",    "state"]
            ]
        }
]

Enums_by_sensor_name = {
    "wifi_level": [
        "NO_SIGNAL",
        "WEAK",
        "NORMAL",
        "STRONG"
    ],
    "gsmNetworkStatus": [
        "UNKNOWN",
        "GSM",
        "2G",
        "3G",
        "4G",
        "5G"
    ],
    "simCardState": [
        "OK",
        "MISSING",
        "MALFUNCTION",
        "LOCKED",
        "UNKNOWN"
    ]
}
