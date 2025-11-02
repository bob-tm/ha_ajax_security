"""Constants for openHAB."""
from datetime import timedelta
from logging import Logger, getLogger

# Base component constants
NAME = "Jeedom Ajax Bridge"
DOMAIN = "ajax_jeedom"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
LOGGER: Logger = getLogger(__package__)

# Platforms
BINARY_SENSOR = "binary_sensor"
SENSOR = "sensor"
SWITCH = "switch"
BUTTON = 'button'
PLATFORMS = [SENSOR, BINARY_SENSOR, BUTTON, SWITCH]

BinarySensors = ['online', 'masked', 'reedClosed', 'realState', 'extraContactClosed', 'tampered', 'externallyPowered', 'armed', 'night_mode_armed', 'leakDetected']
Diagnostic    = ['event', 'eventTag', 'eventCode', 'eventTextShort', 'eventJson', 'eventMalfunctions', 'eventArmingState', 'batteryChargeLevelPercentage', 'batteryCharge', 'wifi_level', 'nightModeArm', 'switchState', 'signalLevel', 'online', 'gsmNetworkStatus', 'buzzerState']

SWITCH_ENABLED = ['Relay', 'WallSwitch', 'Socket']
# Configuration and options
CONF_BASE_URL = "base_url"
CONF_AUTH_TOKEN = "auth_token"
CONF_PANIC_BUTTON = "panic_button"
CONF_API_URL = '/plugins/ajaxSystem/core/php/jeeAjaxSystem.php'


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
-------------------------------------------------------------------
"""
