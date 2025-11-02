# Jeedom Ajax Bridge

# Early UNTESTED VERSION

Fully Integrate Ajax to Home Assistant via Jeedom 

# Jeedom
Please google how to setup Jeedom with Ajax and MQTT Manager plugin.
This integration needs
1. Jeedom with external Access (system->configuration->Networks->External access)
2. API Key from Jeedom (sysyem->configuration->APIs->API Key)
3. Configure Jeedom to use HA MQTT server. I did it with Wireguard Client addon on HA side and Wireguard server on JeeDom side.

   
## HACS Installation

1. Go to http://homeassistant.local:8123/hacs/integrations
1. Add `https://github.com/bob-tm/ha-qingping` custom integration repository
1. Go to http://homeassistant.local:8123/config/integrations and add new integration
1. Choose "Jeedom Ajax Bridge" from the list and follow the config flow steps
3. Check checkbox to Enable Panic Button calls. Without checkbox calls will raise internals exception. Better to disable it while testing.
