# Jeedom Path

/plugins/ajaxSystem/core/php/jeeAjaxSystem.php
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
