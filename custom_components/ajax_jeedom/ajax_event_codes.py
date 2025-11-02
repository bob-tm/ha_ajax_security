#how-to-use-enterprise-API.pdf


ajax_event_codes = {
    "M_01_20": "%3$s: open, %1$s in %2$s",
    "M_01_21": "%3$s: closed, %1$s in %2$s",
    "M_01_22": "%3$s: external contact open, %1$s in %2$s",
    "M_01_23": "%3$s: external contact closed, %1$s in %2$s",
    "M_01_24": "%3$s: alarm is detected, roller shutter %1$s in %2$s",
    "M_01_25": "%3$s: connection lost, roller shutter %1$s in %2$s",
    "M_01_26": "%3$s: connection restored, roller shutter %1$s in %2$s",
    "M_02_20": "%3$s: motion detected, %1$s in %2$s",
    "M_03_20": "%3$s: smoke detected, %1$s in %2$s",
    "M_03_21": "%3$s: no smoke detected, %1$s in %2$s",
    "M_03_22": "%3$s: temperature above the threshold value, %1$s in %2$s",
    "M_03_23": "%3$s: temperature below the threshold value, %1$s in %2$s",
    "M_03_24": "%3$s: hardware failure, %1$s in %2$s",
    "M_03_25": "%3$s: reset after hardware failure, %1$s in %2$s",
    "M_03_26": "%3$s: smoke chamber dirty, %1$s in %2$s",
    "M_03_27": "%3$s: smoke chamber clean, %1$s in %2$s",
    "M_03_28": "%3$s: low reserve battery charge, %1$s in %2$s",
    "M_03_29": "%3$s: reserve battery charged, %1$s in %2$s",
    "M_03_2A": "%3$s: rapid temperature rise detected, %1$s in %2$s",
    "M_03_2B": "%3$s: rapid temperature rise stopped, %1$s in %2$s",
    "M_03_2C": "%3$s: faulty detector %1$s in %2$s. Please, contact the service center listed in the warranty card",
    "M_03_2D": "%3$s: the smoke chamber of %1$s in %2$s is OK",
    "M_04_20": "%3$s: glass break detected, %1$s in %2$s",
    "M_04_22": "%3$s: external contact open, %1$s in %2$s",
    "M_04_23": "%3$s: external contact closed, %1$s in %2$s",
    "M_05_20": "%3$s: water leak detected, %1$s in %2$s",
    "M_05_21": "%3$s: no water leak detected, %1$s in %2$s",
    "M_06_20": "%3$s: motion detected, %1$s in %2$s",
    "M_06_22": "%3$s: masking detected, check the %1$s in %2$s",
    "M_06_23": "%3$s: masking is not detected, %1$s in %2$s",
    "M_07_10": "Updaiting your %1$s firmware",
    "M_07_11": "The firmware of your %1$s has updated successfully",
    "M_07_20": "%3$s: external power failure, %1$s in %2$s",
    "M_07_21": "%3$s: external power restored, %1$s in %2$s",
    "M_08_20": "%3$s: motion detected, %1$s in %2$s",
    "M_08_21": "%3$s: glass break detected, %1$s in %2$s",
    "M_09_20": "%3$s: smoke detected, %1$s in %2$s",
    "M_09_21": "%3$s: no smoke detected, %1$s in %2$s",
    "M_09_22": "%3$s: temperature above the threshold value, %1$s in %2$s",
    "M_09_23": "%3$s: temperature below the threshold value, %1$s in %2$s",
    "M_09_24": "%3$s: hardware failure, %1$s in %2$s",
    "M_09_25": "%3$s: reset after hardware failure, %1$s in %2$s",
    "M_09_26": "%3$s: smoke chamber dirty, %1$s in %2$s",
    "M_09_27": "%3$s: smoke chamber clean, %1$s in %2$s",
    "M_09_28": "%3$s: reserve battery low, %1$s in %2$s",
    "M_09_29": "%3$s: reserve battery charged, %1$s in %2$s",
    "M_09_2A": "%3$s: rapid temperature rise detected, %1$s in %2$s",
    "M_09_2B": "%3$s: rapid temperature rise stopped, %1$s in %2$s",
    "M_09_2C": "%3$s: faulty detector %1$s in %2$s. Please, contact the service center listed in the warranty card",
    "M_09_2D": "%3$s: the smoke chamber of %1$s in %2$s is OK",
    "M_09_30": "%3$s: Carbon monoxide () detected, %1$s in %2$s",
    "M_09_31": "%3$s: Carbon monoxide (CO) level is OK, %1$s in %2$s",
    "M_0A_20": "%3$s: Disarmed using %1$s",
    "M_0A_21": "%3$s: Armed using %1$s",
    "M_0A_22": "%3$s: Night mode activated using %1$s",
    "M_0A_23": "%3$s: Panic button pressed on %1$s",
    "M_0A_24": "%3$s: unsuccessful arming attempt using %1$s",
    "M_0A_25": "%3$s: unsuccessful Night mode activation attempt using %1$s",
    "M_0A_26": "%3$s: the system has been armed with malfunctions using %1$s",
    "M_0A_27": "%3$s: Night mode activated with malfunctions using %1$s",
    "M_0A_28": "%3$s: Night mode deactivated using %1$s",
    "M_0A_29": "%3$s: %2$s has been disarmed using %1$s",
    "M_0A_2A": "%3$s: %2$s has been armed using %1$s",
    "M_0A_2D": "%3$s: %2$s has been armed with malfunctions using %1$s",
    "M_0A_2E": "%3$s: %2$s unsuccessful arming attempt using %1$s",
    "M_0A_2F": "%3$s: %2$s has been disarmed using %1$s",
    "M_0A_30": "%3$s: Attempt to break the password on %1$s",
    "M_0A_31": "%3$s: Disarmed using %1$s",
    "M_0A_32": "%3$s: Night mode deactivated using %1$s",
    "M_0B_02": "%3$s: %1$s battery charged",
    "M_0B_03": "%3$s: low battery level in %1$s",
    "M_0B_20": "%3$s: Disarmed using %1$s",
    "M_0B_21": "%3$s: Armed using %1$s",
    "M_0B_22": "%3$s: Night mode activated using %1$s",
    "M_0B_23": "%3$s: Panic button pressed on %1$s",
    "M_0B_24": "%3$s: unsuccessful arming attempt using %1$s",
    "M_0B_25": "%3$s: unsuccessful Night mode activation attempt using %1$s",
    "M_0B_26": "%3$s: the system has been armed with malfunctions using %1$s",
    "M_0B_27": "%3$s: Night mode activated with malfunctions using %1$s",
    "M_0B_28": "%3$s: Night mode deactivated using %1$s",
    "M_0B_29": "%3$s: %2$s has been disarmed using %1$s",
    "M_0B_2A": "%3$s: %2$s has been armed using %1$s",
    "M_0B_2D": "%3$s: %2$s has been armed with malfunctions using %1$s",
    "M_0B_2E": "%3$s: %2$s unsuccessful arming attempt using %1$s",
    "M_0C_20": "%3$s: Panic button pressed on %1$s",
    "M_0D_20": "%3$s: motion detected, %1$s in %2$s",
    "M_0E_20": "%3$s: motion detected, %1$s in %2$s",
    "M_0F_20": "%3$s: open, %1$s in %2$s",
    "M_0F_21": "%3$s: closed, %1$s in %2$s",
    "M_0F_22": "%3$s: external contact open, %1$s in %2$s",
    "M_0F_23": "%3$s: external contact closed, %1$s in %2$s",
    "M_0F_24": "%3$s: alarm is detected, roller shutter %1$s in %2$s",
    "M_0F_25": "%3$s: connection lost, roller shutter %1$s in %2$s",
    "M_0F_26": "%3$s: connection restored, roller shutter %1$s in %2$s",
    "M_0F_30": "%3$s: shock detected by %1$s in %2$s",
    "M_0F_31": "%3$s: tilt detected by %1$s in %2$s",
    "M_0F_32": "%3$s: the accelerometer of the %1$s in %2$s room doesn't work properly. Please, contact the service center listed in the warranty card",
    "M_0F_33": "%3$s: the accelerometer of the %1$s in %2$s is OK",
    "M_11_20": "%3$s: alarm is detected, %1$s in %2$s",
    "M_11_21": "%3$s: recovered after alarm, %1$s in %2$s",
    "M_11_22": "%3$s: alarm is detected, %1$s in %2$s",
    "M_11_26": "%3$s: %1$s was moved in %2$s",
    "M_12_20": "%3$s: %1$s disabled in %2$s, overheated",
    "M_12_21": "%3$s: Temperature is OK, %1$s in %2$s",
    "M_12_22": "%3$s: %1$s enabled in %2$s",
    "M_12_23": "%3$s: %1$s disabled in %2$s",
    "M_12_28": "%3$s: %1$s disabled in %2$s, maximum voltage threshold reached",
    "M_12_29": "%3$s: %1$s disabled in %2$s, minimum voltage threshold reached",
    "M_12_2A": "%3$s: Voltage is OK, %1$s in %2$s",
    "M_12_2C": "%3$s: Relay for %1$s in %2$s is not responding. Please run a signal strength test.",
    "M_13_20": "%3$s: motion detected, %1$s in %2$s",
    "M_13_22": "%3$s: masking detected, check the %1$s in %2$s",
    "M_13_23": "%3$s: masking is not detected, %1$s in %2$s",
    "M_13_24": "%3$s: external power failure, %1$s in %2$s",
    "M_13_25": "%3$s: external power restored, %1$s in %2$s",
    "M_14_20": "%3$s: %1$s was moved in %2$s",
    "M_14_21": "%3$s: external power failure, %1$s in %2$s",
    "M_14_22": "%3$s: external power restored, %1$s in %2$s",
    "M_1E_20": "%3$s: %1$s disabled in %2$s, overheated",
    "M_1E_21": "%3$s: Temperature is OK, %1$s in %2$s",
    "M_1E_22": "%3$s: %1$s enabled in %2$s",
    "M_1E_23": "%3$s: %1$s disabled in %2$s",
    "M_1E_24": "%3$s: %1$s disabled in %2$s, short circuit",
    "M_1E_25": "%3$s: %1$s disabled in %2$s, maximum current threshold reached",
    "M_1E_26": "%3$s: %1$s disabled in %2$s, user-defined maximum current threshold reached",
    "M_1E_27": "%3$s: Power usage is OK, %1$s in %2$s",
    "M_1E_28": "%3$s: %1$s disabled in %2$s, maximum voltage threshold reached",
    "M_1E_29": "%3$s: %1$s disabled in %2$s, minimum voltage threshold reached",
    "M_1E_2A": "%3$s: Voltage is OK, %1$s in %2$s",
    "M_1E_2C": "%3$s: Socket for %1$s in %2$s is not responding. Please run a signal strength test.",
    "M_1F_20": "%3$s: %1$s disabled in %2$s, overheated",
    "M_1F_21": "%3$s: Temperature is OK, %1$s in %2$s",
    "M_1F_22": "%3$s: %1$s enabled in %2$s",
    "M_1F_23": "%3$s: %1$s disabled in %2$s",
    "M_1F_24": "%3$s: %1$s in %2$s hasn’t switched off. The relay stopped functioning. Disconnect electrical appliances and replace the WallSwitch.",
    "M_1F_25": "%3$s: %1$s disabled in %2$s, maximum current threshold reached",
    "M_1F_26": "%3$s: %1$s disabled in %2$s, user-defined maximum current threshold reached",
    "M_1F_27": "%3$s: Power usage is OK, %1$s in %2$s",
    "M_1F_28": "%3$s: %1$s disabled in %2$s, maximum voltage threshold reached",
    "M_1F_29": "%3$s: %1$s disabled in %2$s, minimum voltage threshold reached",
    "M_1F_2A": "%3$s: Voltage is OK, %1$s in %2$s",
    "M_1F_2C": "%3$s: WallSwitch for %1$s in %2$s is not responding. Please run a signal strength test.",
    "M_21_00": "%1$s: external power failure",
    "M_21_01": "%1$s: external power restored",
    "M_21_02": "%1$s: battery low",
    "M_21_03": "%1$s: battery charged",
    "M_21_04": "%1$s: lid open",
    "M_21_05": "%1$s: lid closed",
    "M_21_06": "%1$s: GSM signal level poor",
    "M_21_07": "%1$s: GSM signal level OK",
    "M_21_08": "%1$s: radio-frequency interference level is high",
    "M_21_09": "%1$s: radio-frequency interference level is OK",
    "M_21_0A": "%1$s: Hub is offline. Check mobile signal strength and the Ethernet port",
    "M_21_0B": "%1$s: Hub is online again",
    "M_21_0C": "%1$s: turned off",
    "M_21_10": "%1$s: updating firmware...",
    "M_21_11": "%1$s: firmware updated",
    "M_21_12": "%1$s: Malfunction!",
    "M_21_13": "%1$s: connection to the monitoring station is lost. Check mobile signal strength and the Ethernet port on the Hub",
    "M_22_00": "%3$s: Disarmed by %1$s",
    "M_22_01": "%3$s: Armed by %1$s",
    "M_22_02": "%3$s: Night mode activated by %1$s",
    "M_22_03": "%3$s: %1$s pressed the panic button",
    "M_22_07": "%3$s: new user %1$s has been added",
    "M_22_08": "%3$s: user %1$s has been removed",
    "M_22_09": "%2$s has allowed access to the hub settings to %1$s (%4$s) for %3$s hours",
    "M_22_0A": "%2$s has allowed a permanent access to the hub settings to %1$s (%4$s)",
    "M_22_0B": "%2$s has denied access to the hub settings to %1$s (%4$s)",
    "M_22_0D": "PRO user has requested access to the hub settings",
    "M_22_24": "%3$s: unsuccessful arming attempt by %1$s",
    "M_22_25": "%3$s: unsuccessful Night mode activation attempt by %1$s",
    "M_22_26": "%3$s: the system has been armed with malfunctions by %1$s",
    "M_22_27": "%3$s: Night mode activated with malfunctions by %1$s",
    "M_22_28": "%3$s: Night mode deactivated by %1$s",
    "M_22_29": "%3$s: %2$s has been disarmed by %1$s",
    "M_22_2A": "%3$s: %2$s has been armed by %1$s",
    "M_22_2D": "%3$s: %2$s has been armed with malfunctions by %1$s",
    "M_22_2E": "%3$s: %2$s unsuccessful arming attempt by %1$s",
    "M_22_2F": "%3$s: %2$s has been disarmed by %1$s",
    "M_22_31": "%3$s: Disarmed by %1$s",
    "M_22_32": "%3$s: Night mode deactivated by %1$s",
    "M_23_08": "%3$s: new group %1$s has been added",
    "M_23_09": "%3$s: group %1$s has been removed",
    "M_24_08": "%3$s: room %2$s has been added",
    "M_24_09": "%3$s: room %2$s has been removed",
    "M_25_08": "%3$s: new camera %1$s has been added",
    "M_25_09": "%3$s: camera %1$s has been removed",
    "M_26_00": "%3$s: lid open, %1$s in %2$s",
    "M_26_01": "%3$s: lid closed, %1$s in %2$s",
    "M_26_20": "%3$s: alarm is detected, %1$s in %2$s",
    "M_26_21": "%3$s: recovered after alarm, %1$s in %2$s",
    "M_26_22": "%3$s: alarm is detected, %1$s in %2$s",
    "M_26_23": "%3$s: external contact is shorted out, %1$s in %2$s",
    "M_26_24": "%3$s: external contact is OK, %1$s in %2$s",
    "M_ABS_00": "%3$s: lid open, %1$s in %2$s",
    "M_ABS_01": "%3$s: lid closed, %1$s in %2$s",
    "M_ABS_02": "%3$s: battery charged, %1$s in %2$s",
    "M_ABS_03": "%3$s: low battery, %1$s in %2$s",
    "M_ABS_04": "%3$s: connection lost, %1$s in %2$s",
    "M_ABS_05": "%3$s: connection restored, %1$s in %2$s",
    "M_ABS_06": "%3$s: synchronization failure, %1$s in %2$s",
    "M_ABS_07": "%3$s: synchronization OK, %1$s in %2$s",
    "M_ABS_08": "%3$s: %1$s has been added successfully",
    "M_ABS_09": "%3$s: %1$s has been removed",
    "M_ABS_10": "Updaiting your %1$s firmware",
    "M_ABS_11": "The firmware of your %1$s has updated successfully",
    "M_ABS_12": "%3$s: %1$s in %2$s has detected a malfunction",
    "M_ABS_13": "%1$s turned off"
}

ajax_event_codes_reversed = {
	'M_12_37'	  : '%3$s: switched on, %1$s in %2$s',
	'M_12_46'	  : '%3$s: switched off, %1$s in %2$s',
	'M_12_34'	  : '%3$s: switched on by arming, %1$s in %2$s',
	'M_12_40'	  : '%3$s: switched off by disarming, %1$s in %2$s',
	'M_ABS_0A'	  : '%3$s: %1$s in %2$s Temporarily deactivated'
}


# Here is an example of event codes translation for EN locale in json format but we can provide translations in a big variety of languages and
# formats.
# Placeholders are
# "M_01_20": "%3$s: open, %1$s in %2$s",
# M -signal type, the static parameter for all signal and doesn't change.
# 01 - device type. More detailed at APPENDIX B
# 20 - event signal "open"-description is contained in each event
# %3 - hub name
# %1 - event source object name (e.g. sensor name)
# %2 - event room name

def AjaxTranslateEvent(eventcode, sourceobjectname, eventroomname):
	if eventcode in ajax_event_codes:
		return ajax_event_codes[eventcode].replace("%1$s", sourceobjectname).replace("%2$s", eventroomname).replace("%3$s: ", '')
	elif eventcode in ajax_event_codes_reversed:
		return ajax_event_codes_reversed[eventcode].replace("%1$s", sourceobjectname).replace("%2$s", eventroomname).replace("%3$s: ", '')

		return f"{eventcode} in {eventroomname} by {sourceobjectname}"

'''
 Device number Device Type
 01 Door Protect
 02 Motion Protect
 03 Fire Protect
 04 Glass Protect
 05 Leak Protect
 06 Motion Protect Curtain
 07 Range Extender
 08 CombiProtect
 09 Fire Protect Plus
 0A Keypad
 0B Space Control
 0C Button
 0D MotionCam
 0E Motion Protect Plus
 0F Door Protect Plus
 11 Transmitter
 12 Relay
 13 Motion Protect Outdoor
 14 Street Siren
 15 Home Siren
 1F Wall Switch
 1E Socket
 22 User
 23 Group
 24 Room
 25 Camera
 ABS Common part for all device


 Device States
 State Description
 0 PASSIVE
 1 ACTIVE
 2 DETECTION_AREA_TEST
 3 RADIO_CONNECTION_TEST
 4 WAIT_RADIO_CONNECTION_TEST_START
 5 WAIT_RADIO_CONNECTION_TEST_END
 6 WAIT_DETECTION_AREA_TEST_START
 7 WAIT_DETECTION_AREA_TEST_END
 8 WAIT_REGISTRATIO
'''