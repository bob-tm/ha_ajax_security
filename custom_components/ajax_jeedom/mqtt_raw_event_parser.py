HubArmTags 	  	= ['ArmAttempt', 'Arm', 'ArmWithMalfunctions', 'Disarm']
GroupArmTags  	= ['GroupArmAttempt', 'GroupArm', 'GroupArmWithMalfunctions', 'GroupDisarm']
NightModeArmTags= ['NightModeOnAttempt', 'NightModeOn', 'NightModeOnWithMalfunctions', 'NightModeOff']

ArmOk 	   = ['Arm', 'GroupArm', 'NightModeOn']
ArmAttempt = ['ArmAttempt', 'GroupArmAttempt', 'NightModeOnAttempt']
WithErrors = ['ArmWithMalfunctions', 'GroupArmWithMalfunctions', 'NightModeOnWithMalfunctions']
Disarm     = ['Disarm', 'NightModeOff', 'GroupDisarm']


Relay      = ['RelayOnByDisarming', 'RelayOnByArming', 'RelayOnByUser']

HubArmed     = ['Arm','ArmWithMalfunctions']
HubNotArmed  = ['ArmAttempt','Disarm']

STATE_ARMED      			= 'Armed'
STATE_DISARMED   			= 'Disarmed'
STATE_ARMATTEMPT 			= 'ArmAttempt'
STATE_ARMED_WITH_ERRORS 	= 'ArmedWithErrors'
STATE_HUB_CHECK_GROUPS  	= 'CHECK_GROUPS'
STATE_HUB_PARTIALLY_ARMED  	= 'PartiallyArmed'
STATE_EXEC_CMD				= 'Request'



UserText = {
	'Arm'		  : 'Armed',
	'Disarm'	  : 'Disarmed',
	'NightModeOn' : 'Night Mode ON',
	'NightModeOff': 'Night Mode OFF'
}

HubArmTags2States = {
	'ArmAttempt' 			: STATE_ARMATTEMPT,
	'Arm'		  			: STATE_ARMED,
	'ArmWithMalfunctions'	: STATE_ARMED_WITH_ERRORS,
	'Disarm'	  			: STATE_DISARMED,

}

HubStates = {
	'ARMED'		  		: STATE_ARMED,
	'DISARMED'	  		: STATE_DISARMED,
	'PARTIALLY_ARMED' 	: STATE_HUB_PARTIALLY_ARMED,
}

from .ajax_event_codes import AjaxTranslateEvent

AjaxLog2Config = {
	'RELAY.voltage' 	: 'voltageMilliVolts',
	'HUB.hubPowered'	: 'externallyPowered',
	'HUB.batteryCharge'	: 'batteryCharge',
	'GROUP.state'		: 'armed',
	'externalPower'		: 'externallyPowered', 	# MOTION_PROTECT_OUTDOOR, STREET_SIREN
	'isMasked'			: 'masked',				# MotionProtectOutdoor
	'serviceProblems'				: False,	# send for low-battery and disabled devices.
	'HUB.CMSActiveChannels'			: False,	# 2,4,6 looks like bitmask for usage of WIFI ang GSM
	'HUB.wifi_gate'					: False, 	# -1062731775 ????
	'HUB.soundIndicationsStatus'	: False,	# 0
	'HUB.batterySaveModeStatus'		: False,	# 0
	'HUB.modemImei'					: False,	# imei number,
	'batteryChargeVolt'				: False,	# 25, 26, 27
	'fw_code'						: False,	# 0,
	'batteryOk'						: False,	# 1
	'synchroOk'						: False,	# 0, 1
	'capabilities'					: False		# -124
}


AjaxLog2ConfigUnknown = {

}


AjaxHubEventSensors = ['event', 'eventTag', 'eventCode', 'eventText', 'eventTextShort', 'eventMalfunctions', 'eventSecurity']

def HubStateToLowerCaseState(s):
	return HubStates[s] if s in HubStates else s

def SensorNameFromLogToConfig(log):
	fn = f"{log['type']}.{log['name']}"

	if fn in AjaxLog2Config:
		return AjaxLog2Config[fn]
	elif log['name'] in AjaxLog2Config:
		return AjaxLog2Config[log['name']]
	else:
	    return log['name']

def HumanText(s):
	if s in UserText:
		return UserText[s]
	else:
		return s

def ArmMode2Text(am):
	#return am
	am = am.replace('Group', '').replace('WithMalfunctions', '').replace('Attempt', '')
	return HumanText(am)


def DeviceMalfunctions(event):
	result = ''
	if 'additionalDataV2' in event:
		DataV2 = event['additionalDataV2']
		if DataV2:
			for ad in DataV2:
				if ad['additionalDataV2Type']=='TROUBLED_DEVICES':
					dm = ad['troubleDevices']
					if dm:
						for d in dm:
							m = f"{AjaxTranslateEvent(d['text'], d['sourceName'], d['roomName'])}"
							result = f"{result}; {m}".lstrip(';').lstrip()

	return result

def GroupsInfoV1(event):
	result = None
	if 'additionalData' in event:
		ad = event['additionalData']
		if ad and ad['additionalDataType']=='DEVICE_MALFUNCTIONS':
			rgi  = ad['relatedGroupsInfo']
			if rgi:
				text = ''

				for g in rgi:
					m = f"{g['name']}"
					text = f"{text}; {m}".lstrip(';').lstrip()

				result = {'groups': rgi, 'text': text}

	return result

def GroupsInfoV2(event):
	result = ''
	groups = False
	if 'additionalDataV2' in event:
		DataV2 = event['additionalDataV2']
		if DataV2:
			for ad in DataV2:
				if ad['additionalDataV2Type']=='DISPLAY_GROUPS':
					groups = ad['displayEventGroups']
					if groups:
						for g in groups:
							m = f"{g['groupName']}"
							result = f"{result}; {m}".lstrip(';').lstrip()

	return {
		'text'  : result,
		'groups': groups
	}


def get_arming_state(e):
	result = {
		'message'		: '',
		'arming_state'	: None,
		'armed'			: None
	}

	if 'eventTag' in e:
		eventTag = e['eventTag']
		target   = ''

		if   eventTag in ArmAttempt		: arming_state = STATE_ARMATTEMPT
		elif eventTag in ArmOk			: arming_state = STATE_ARMED
		elif eventTag in WithErrors		: arming_state = STATE_ARMED_WITH_ERRORS
		elif eventTag in Disarm			: arming_state = STATE_DISARMED
		else							: arming_state = eventTag

		if eventTag in NightModeArmTags		: target = 'Night Mode'
		elif eventTag in GroupArmTags		: target = e['sourceRoomName']
		elif eventTag in HubArmTags			: target = 'Hub'

		#if eventTag in NightModeArmTags		: result['states']['nightmode']	= arming_state
		#elif eventTag in GroupArmTags		: result['states']['group'] 	= arming_state
		#elif eventTag in HubArmTags			: result['states']['hub'] 		= arming_state

		if eventTag in HubArmTags	: result['hub_armed'] = HubArmTags2States[eventTag]
		#if eventTag in HubArmed		: result['hub_armed'] = STATE_ARMED
		#if eventTag in HubNotArmed	: result['hub_armed'] = STATE_DISARMED
		if eventTag in GroupArmTags	: result['hub_armed'] = STATE_HUB_CHECK_GROUPS

		result['message'] 		= f"{target} {arming_state}"
		result['arming_state']	= arming_state
		result['armed']			= (eventTag in ArmOk) or (eventTag in WithErrors)


	return result


def add_update_param(update, id, sensor_name, value, title=None):
	j = {
		'id': id,
		'type'  : 'SECURITY_EVENT_PARSED',
		'name'	: sensor_name,
		'state' : value,
	}

	if title:
		j['title']=title

	update.append(j)

def parse_raw_message(m):
	updates = []
	event   = None
	user_id = None
	hub_id  = None
	debugText = None

	if 'updates' in m:
		upd 	= m['updates']
		user_id = m['userId']
		hub_id  = m['hubId'  ]

		for key in upd:
			kv = {
					'id'	: m['id'],
					'type'	: m['type'], 	# HUB, GROUP, COMBI_PROTECT, MOTION_PROTECT_PLUS, MOTION_PROTECT_OUTDOOR, RELAY, DOOR_PROTECT, STREET_SIREN
					'name'  : key,
					'state' : upd[key]
			}
			updates.append(kv)

	if 'event' in m:
		e = m['event']

		hub_id   = e['hubId']

		eventTag 	= e['eventTag'] 	if 'eventTag' in e else ''
		transition	= e['transition']	if 'transition' in e else ''

		debugText = eventTag

		message = ''

		event = {
				'eventType' : e['eventTypeV2'],
				'eventTag'  : eventTag,
				'eventCode'	: e['eventCode'],
				'eventText'	: AjaxTranslateEvent(e['eventCode'], e['sourceObjectName'], e['sourceRoomName']),
				'sourceObj'	: e['sourceObjectName'],
				'sourceObjectId'  : e['sourceObjectId'],
				'additionalDataV2': e['additionalDataV2'],
				'transition': transition
		}

		event_Alarm    = False
		event_Security = False

		if m['recipient']:
			if m['recipient']['type']=='USER':
				user_id = m['recipient']['id']

		if e['eventTypeV2'] in ['ALARM', 'ALARM_RECOVERED']:
			# Add ALARM events, to security log
			# It's much easy to dislay one log in UI
			event_Security = event['eventText']

		elif e['eventTypeV2']=='SECURITY':
			event_Security			= event['eventText']
			event_Malfunctions      = DeviceMalfunctions(e)
			groups_info_v1			= GroupsInfoV1(e)
			groups_info_v2			= GroupsInfoV2(e)
			arming_info				= get_arming_state(e)

			debugText 	 			= arming_info['message']
			hub_state				= None

			#(message, arming_state) = get_event_short_text(e)

			# Calculate NIGHT MODE state
			if eventTag in NightModeArmTags:
				add_update_param(updates, hub_id, 'night_mode_armed', 		arming_info['armed'])
				add_update_param(updates, hub_id, 'night_mode_state', arming_info['arming_state'])


			if eventTag in HubArmTags:
				# Calculate GROUP state after HUB Arm actions
				if groups_info_v1:
					debugText = f"{debugText}: {groups_info_v1['text']}"
					for g in groups_info_v1['groups']:
						add_update_param(updates, g['id'], 'armed', arming_info['armed'], 			g['name'])
						add_update_param(updates, g['id'], 'state', arming_info['arming_state'], 	g['name'])

			# Calculate GROUP state update after GroupArmAction
			if groups_info_v2['groups']:
				for g in groups_info_v2['groups']:
					add_update_param(updates, g['groupId'], 'armed', 	arming_info['armed'], 			g['groupName'])
					add_update_param(updates, g['groupId'], 'state', 	arming_info['arming_state'], 	g['groupName'])


			#add_update_param(updates, hub_id, 'eventArmingState',  arming_info['arming_state'])
			add_update_param(updates, hub_id, 'eventMalfunctions', event_Malfunctions)


			if 'hub_armed' in arming_info:
				add_update_param(updates, hub_id, 'hub_state', arming_info['hub_armed'])

				#if arming_info['hub_armed'] == 'DISARMED': 	event_Alarm = ''

				#if arming_info['hub_armed'] != 'CHECK_GROUPS':
				#	add_update_param(updates, hub_id, 'hub_state', arming_info['arming_state'])

			message = debugText
		elif e['eventTypeV2']=='SMART_HOME_ACTUATOR':
			prefix  = "Relay" if eventTag in Relay else f"{eventTag}"
			message = f"{prefix} {e['sourceRoomName']} {HumanText(e['eventCode'])}" # + json.dumps(e)

			realState = None
			if e['eventCode'] in ['M_12_46', 'M_12_40']: 	#switched off, дом in дом
				realState = False
				debugText = f"{prefix} switched off, {debugText}"
			elif e['eventCode'] in ['M_12_37', 'M_12_34']:	#switched on дом in дом
				realState = True
				debugText = f"{prefix} switched on, {debugText}"

			if realState != None:
				kv = {
							'id'	: e['sourceObjectId'],
							'type'  : 'API_ARM_STATE_UPDATE',
							'name'	: 'realState',
							'state' : realState
				}
				updates.append(kv)

		else:
			message = f"{e['eventTypeV2']}: {e['sourceRoomName']} {eventTag} {HumanText(e['eventCode'])}" # + json.dumps(e)

		#event['human_text'  ] = message

		params = [
				{'name':'event', 			'state': event['eventType']},
				{'name':'eventTag', 		'state': event['eventTag' ]},
				{'name':'eventCode', 		'state': event['eventCode']},
				{'name':'eventText', 		'state': event['eventText']},
				{'name':'eventTextShort', 	'state': message.strip()},
				#{'name':'sourceObjectName',	'state': event['sourceObj']},
				#{'name':'sourceObjectId',	'state': e['sourceObjectId']},
				#{'name':'eventJson',		'state': event},
		]

		#if event_Alarm:    params.append({'name': 'eventAlarm',    'state': event_Alarm})
		if event_Security: params.append({'name': 'eventSecurity', 'state': event_Security})

		for p in params:
			updates.append({'id': hub_id, 'type': 'API_EVENT_UPDATE', 'name': p['name'], 'state':p['state']})

	return {
		'updates'  : updates,
		'event'	   : event,
		'debug'	   : debugText,
		'user_id'  : user_id,
		'hub_id'   : hub_id
	}

'''
  ProtoHub:
	state:
        description: "If group mode is disabled then possible values are: DISARMED, ARMED, NIGHT_MODE. Otherwise one of the remaining values will be returned."
        enum:
          - DISARMED
          - ARMED
          - NIGHT_MODE
          - ARMED_NIGHT_MODE_ON
          - ARMED_NIGHT_MODE_OFF
          - DISARMED_NIGHT_MODE_ON
          - DISARMED_NIGHT_MODE_OFF
          - PARTIALLY_ARMED_NIGHT_MODE_ON
          - PARTIALLY_ARMED_NIGHT_MODE_OFF



          - DISARMED
          - ARMED
		  - PARTIALLY_ARMED

          - NIGHT_MODE
          - ARMED_NIGHT_MODE_ON
          - ARMED_NIGHT_MODE_OFF
          - DISARMED_NIGHT_MODE_ON
          - DISARMED_NIGHT_MODE_OFF
          - PARTIALLY_ARMED_NIGHT_MODE_ON
          - PARTIALLY_ARMED_NIGHT_MODE_OFF


  EventTypeV2:
    description: "COMMON eventTypeV2 is deprecated"
    type: "string"
    enum:
      - ALARM
      - ALARM_RECOVERED
      - MALFUNCTION
      - FUNCTION_RECOVERED
      - SECURITY
      - COMMON
      - USER
      - LIFECYCLE
      - SYSTEM
      - SMART_HOME_ACTUATOR
      - SMART_HOME_ALARM
      - SMART_HOME_ALARM_RECOVERED
      - SMART_HOME_EVENT
      - SMART_HOME_MALFUNCTION
      - ALARM_WARNING
      - VIDEO_MOTION
      - VIDEO_HUMAN
      - VIDEO_PET
      - VIDEO_VEHICLE
      - VIDEO_SCENARIO_EXECUTED
      - VIDEO_RING_BUTTON_PRESSED
'''