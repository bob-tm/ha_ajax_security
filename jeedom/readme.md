# Jeedom Install
Plese Install Jeedom + MQTT Manager + Ajax System (8 euro one time, in Jeedom Market, it defenetly costs this money)

# Jeedom COnfiguration
It's mandatory to apply code path and configure Jeedom, before Home Assistant Integration Configuration! 

Open Settings
![image](https://github.com/bob-tm/ha_ajax_security/blob/main/jeedom/system_config.png)

# External Access
It is ABSOLUTELY necessary that your Jeedom be accessible from the outside (external access URL used)
Setup it here. 
![image](https://github.com/bob-tm/ha_ajax_security/blob/main/jeedom/ext_url.png)

I use wireguard tunel (wiregiuard client Addon) from my HA to my server with white IP. MQTT client connects to wireguard IP to push updages to HA MQTT server. Or you can use port translation to open external access to mqtt server behind NAT

# Jeedom Path

We need to path Jeedom Code, to acccess all functions in Ajax API. From Jeedom we use only two functions. 
- ajaxSystem::request to call Ajax API via Jeedom Market gateway
- redirect events from Ajax API to mqtt, before Jeedom will parse it.

Jeedom used to first login and manage tokens to access Ajax API. It's possible to rewrite ajaxSystem::request localy and do not use Jeedom at all. If you want - you can help, it's not a lot of code, but more about testing :) I see it like small HA addon, that listen public url for Ajax API Events and redirect everything to MQTT 

1. Open build in Code Editor
![image](https://github.com/bob-tm/ha_ajax_security/blob/main/jeedom/editor.png)

2. Locate File /plugins/ajaxSystem/core/php/jeeAjaxSystem.php
![image](https://github.com/bob-tm/ha_ajax_security/blob/main/jeedom/ajaxphp.png) 

3. Copy Paste selected code and save. Just after Log::Add
![image](https://github.com/bob-tm/ha_ajax_security/blob/main/jeedom/path.png)

```php
if (class_exists('mqtt2', true)) {
  if (isset($datas['ha_direct_call'])) {
   	$func = $datas['ha_direct_call'];
     
    if ($func=='get_userId') {
    	$data = ['userId' => config::byKey('userId', 'ajaxSystem'), 'test'=>'ok'];
      	echo json_encode($data);
    	http_response_code(200);
 		die();
    } elseif ($func=='AjaxApi') {
    	$ajax_path = $datas['a_path'];
    	$ajax_data = $datas['a_data'];
    	$ajax_type = $datas['a_type'];    
      	try {
        	$rr = ajaxSystem::request($ajax_path, $ajax_data, $ajax_type);
          	$r = ['result' => $rr];
      	}
        catch(Exception $e) {
          	$r = ['exception' => $e->getMessage()];
        }
      	echo json_encode($r);
      
      	http_response_code(200);
 		die();
    }
    
    http_response_code(500);
 	die();
    
  } else {
  	mqtt2::publish('jeedom/raw/event', json_encode($datas));
  }
}
```

# Ajax API Key
To Setup Home Assistant Integartion you need:
- External Access URL
- This Ajax API key
 

![image](https://github.com/bob-tm/ha_ajax_security/blob/main/jeedom/ajax_api.png)

# Updates
It's better to disable everything
![image](https://github.com/bob-tm/ha_ajax_security/blob/main/jeedom/updates1.png)
![image](https://github.com/bob-tm/ha_ajax_security/blob/main/jeedom/updates2.png)




