<?php
declare(strict_types=1);

header('Content-Type: application/json');
$config = [];
$mqttStatus = 'error';
$eventData = null;
$mqttError = null;
$startedAt = microtime(true);

function debugLog(int $status, string $message): void
{
    global $config, $startedAt, $mqttStatus, $eventData, $mqttError;
    if (empty($config['debug'])) {
        return;
    }
    $entry = ['mqtt' => $mqttStatus];
    if (!empty($config['debug_events']) && $eventData !== null) {
        $entry['data'] = $eventData;
    }
    $entry['time'] = gmdate('c');
    $entry['status'] = $status;
    $entry['result'] = $message;
    $entry['duration_ms'] = round((microtime(true) - $startedAt) * 1000);
    if ($mqttError !== null) {
        $entry['error'] = $mqttError;
    }
    $line = json_encode($entry, JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE);
    $file = $config['debug_log'] ?? '';
    if ($file === '') {
        error_log('Ajax bridge: ' . $line);
    } elseif (@file_put_contents($file, $line . PHP_EOL, FILE_APPEND | LOCK_EX) === false) {
        error_log('Ajax bridge: cannot write debug log.');
    }
}

function respond(int $status, string $message): void
{
    debugLog($status, $message);
    http_response_code($status);
    echo json_encode(['message' => $message]);
    exit;
}

$configFile = __DIR__ . '/config.php';
if (!is_file($configFile)) {
    respond(503, 'Bridge configuration is missing.');
}
$config = require $configFile;
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    respond(405, 'Use POST.');
}


$token = $config['callback_token'] ?? '';
if (!is_string($token) || $token === '' || $token === 'CHANGE_ME') {
    respond(503, 'Configure the callback token.');
}

// Bound the body before decoding or sending it to the broker.
$raw = file_get_contents('php://input', false, null, 0, 1048577);
if ($raw === false || strlen($raw) > 1048576) {
    respond(413, 'Request body is too large.');
}
try {
    $data = json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
} catch (JsonException $error) {
    respond(400, 'Invalid JSON.');
}
if (!is_array($data) || !is_string($data['apikey'] ?? null) || !hash_equals($token, $data['apikey'])) {
    respond(403, 'Invalid callback token.');
}
if (!isset($data['data']) || !is_array($data['data'])) {
    respond(400, 'Missing event data.');
}

$eventData = $data['data'];
require_once __DIR__ . '/lib/MqttPublisher.php';
try {
    MqttPublisher::publish($config['mqtt'], 'jeedom/raw/event', $raw);
} catch (Throwable $error) {
    $mqttError = $error instanceof RuntimeException ? $error->getMessage() : 'Invalid configuration or internal error';
    if (empty($config['debug'])) {
        error_log('Ajax bridge: MQTT delivery failed.');
    }
    respond(503, 'MQTT delivery failed.');
}
$mqttStatus = 'ok';
respond(200, 'Event forwarded.');
