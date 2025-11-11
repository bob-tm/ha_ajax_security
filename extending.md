# How to Add new devices

Integration parse device json at startup and than update it sensors via event messages.

1. Device json file. It saved at \config\\.storage\ajax_jeedom\jeedom_ext_link\user_id\hubs\hub_id\devices\device_id.json  
2. All events are printed to log in debug mode.

To add new features you can:
1. Fork this repo
2. In hub.py Uncoment ```CACHE_AJAX_REQUESTS = True```. Code will use json from disk only, no API.

Logic is simple:
1. Sensors has the same name in device json and event.
   In this case just add sensor name to ```ajax_devices_schema.TryForAllSensors``` array.
   
2. Sensor name is different in json and event.
   Add to ```ajax_devices_schema.EnableSensorsByModel``` or ```ajax_devices_schema.EnableSensorsByDeviceType``` an array with two items ```[sensor_name_in_evet, json_path]```

3. Sensor name in device json and event is different from HA sensor name. In this case
  ```mqtt_raw_event_parser.AjaxLog2Config``` is used to convert sensor name. False means that event is Ignored

if sensor value format in json or event is different from HA format, than is should be converted.

This function convert value from device json to HA
```Hub.AjaxDevice.UpdateSensorFromJson```

This function convert value from event to HA
```Hub.‎AjaxDevice.parse_sensor_value``` 

