# Ajax Security via Jeedom Home Assistant Integartion

First HA Integration, that works!

![image](https://github.com/bob-tm/ha_ajax_security/blob/main/ui/card.jpg)

Technically it uses Ajax API via Jeedom cloud. Jeedom works like a proxy. All commands and events exactly like in Ajax API documentation. This integartion call API and parse events independetly of Jeedom Ajax Plugin. It's provide more features and works much better.

# REQUIREMENTS
- Jeedom with exteral access by url (Jeedom cloud call this url on each Ajax Event)
- Jeedom Ajax System plugin. It's one time 8 euro. It opens access to Ajax API via Jeedom Cloud
- A simple code path to Jeedom installation.
- I do not add ajax@jeedom.com user to my hub (it's jeedom recommendation). Everything works withut this step.
  
!!! It's mandatory to have external access to Jeedom installation !!!

# What is works
- Arm, Force ARM, Disarm for HUB and Groups
- Build in HA Action (service) to Arm / Disarm multiple Groups with one click
- Panic and muteFiredecetcors buttons
- Night Mode, Force Night Mode
- Correct malfunctions messages
- Correct text Messages like in original APP
- Realtime events
- ALARM events
- Sensors with Real time updates for Door sensors, Temperature, PowerFailure, Battery charge, Masking, Relay voltage, and more..
- Relays, Sockets
- Relatime Events
- My [HA User Interface Card](https://github.com/bob-tm/ha_ajax_security/blob/main/ui/readme.md)
- Testing it limited to my equipment. Feedback is welcome!
  
# Installation
1. Install Jeedom + MQTT Manager + Ajax System Plugin.
2. Configure Ajax in Jeedom, Configure Mqtt in Jeedom to access mqtt server, that HA uses
3. It's not required to check "Transmit all equipment" in mqtt manager settings. Itegration do not use this information 
4. [Configure Jeedom by this Manual](https://github.com/bob-tm/ha_ajax_security/blob/main/jeedom/readme.md)
5. Install this integration using HACS
6. Configure access with information from step 4.
7. [Configure UI Card by this Manual](https://github.com/bob-tm/ha_ajax_security/blob/main/ui/readme.md)

   
## HACS Installation

1. Go to http://homeassistant.local:8123/hacs/integrations
1. Add `https://github.com/bob-tm/ha_ajax_security` custom integration repository
1. Go to http://homeassistant.local:8123/config/integrations and add new integration
1. Choose "Ajax Security via Jeedom" from the list and follow the config flow steps
3. Check checkbox to Enable Panic Button calls. Without checkbox calls will raise internals exception. Better to disable it while testing.


