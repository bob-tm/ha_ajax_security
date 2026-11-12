<?php
declare(strict_types=1);

return [
    // Enable request and MQTT diagnostics; credentials are excluded.
    'debug' => false,
    // Include authenticated event data in debug logs; requires debug = true.
    'debug_events' => false,
    // PHP must be able to write here; use '' for the standard PHP error log.
    'debug_log' => __DIR__ . '/bridge-debug.log',
    // Use the same secret in HA's Jeedom Ajax System plugin API key field.
    'callback_token' => 'CHANGE_ME',
    'mqtt' => [
        // Broker address reachable from this web server.
        'host' => '127.0.0.1',
        // Usually 1883 without TLS, or 8883 with TLS.
        'port' => 1883,
        // Leave both credentials empty only if the broker permits anonymous access.
        'username' => '',
        'password' => '',
        // TLS verifies the broker certificate against the system's trusted CAs.
        'tls' => false,
        // Connection and socket timeout, in seconds.
        'timeout' => 5,
    ],
];
