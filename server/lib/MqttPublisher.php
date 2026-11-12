<?php
declare(strict_types=1);

/** Minimal MQTT 3.1.1 publisher: clean session, QoS 1, no retained events. */
final class MqttPublisher
{
    public static function publish(array $config, string $topic, string $payload): void
    {
        $host = $config['host'];
        $port = (int) $config['port'];
        $timeout = (int) ($config['timeout'] ?? 5);
        if ($host === '' || $port < 1 || $port > 65535 || $timeout < 1) {
            throw new RuntimeException('Invalid MQTT connection settings.');
        }
        $context = stream_context_create(['ssl' => [
            'verify_peer' => true,
            'verify_peer_name' => true,
            'peer_name' => $host,
        ]]);
        $address = strpos($host, ':') !== false ? '[' . $host . ']' : $host;
        $socket = @stream_socket_client(
            (($config['tls'] ?? false) ? 'tls' : 'tcp') . '://' . $address . ':' . $port,
            $errno, $error, $timeout, STREAM_CLIENT_CONNECT, $context
        );
        if ($socket === false) {
            throw new RuntimeException('Cannot connect to the MQTT broker.');
        }
        stream_set_timeout($socket, $timeout);
        try {
            $flags = 2; // Clean session avoids storing state between HTTP requests.
            $body = self::field('ajax-bridge-' . bin2hex(random_bytes(8)));
            $username = (string) ($config['username'] ?? '');
            $password = (string) ($config['password'] ?? '');
            if ($username !== '') {
                $flags |= 128;
                $body .= self::field($username);
                if ($password !== '') {
                    $flags |= 64;
                    $body .= self::field($password);
                }
            } elseif ($password !== '') {
                throw new RuntimeException('MQTT password requires a username.');
            }
            self::send($socket, 0x10, self::field('MQTT') . chr(4) . chr($flags) . pack('n', 30) . $body);
            [$type, $response] = self::receive($socket);
            if ($type !== 0x20 || $response !== "\x00\x00") {
                throw new RuntimeException('MQTT connection was rejected.');
            }
            self::send($socket, 0x32, self::field($topic) . pack('n', 1) . $payload);
            [$type, $response] = self::receive($socket);
            if ($type !== 0x40 || $response !== "\x00\x01") {
                throw new RuntimeException('MQTT publish was not acknowledged.');
            }
            self::send($socket, 0xE0, '');
        } finally {
            fclose($socket);
        }
    }

    private static function field(string $value): string
    {
        if (strlen($value) > 65535) {
            throw new RuntimeException('MQTT field is too long.');
        }
        return pack('n', strlen($value)) . $value;
    }

    private static function send($socket, int $header, string $body): void
    {
        $length = strlen($body);
        if ($length > 268435455) {
            throw new RuntimeException('MQTT packet is too large.');
        }
        $packet = chr($header);
        do {
            $digit = $length % 128;
            $length = intdiv($length, 128);
            $packet .= chr($digit | ($length > 0 ? 128 : 0));
        } while ($length > 0);
        $packet .= $body;
        while ($packet !== '') {
            $written = @fwrite($socket, $packet);
            if ($written === false || $written === 0) {
                throw new RuntimeException('Cannot write to the MQTT broker.');
            }
            $packet = substr($packet, $written);
        }
    }

    private static function receive($socket): array
    {
        $header = ord(self::read($socket, 1));
        $length = 0;
        $multiplier = 1;
        for ($index = 0; $index < 4; $index++) {
            $digit = ord(self::read($socket, 1));
            $length += ($digit & 127) * $multiplier;
            if (($digit & 128) === 0) {
                if ($length > 4) {
                    throw new RuntimeException('Unexpected MQTT acknowledgement.');
                }
                return [$header, self::read($socket, $length)];
            }
            $multiplier *= 128;
        }
        throw new RuntimeException('Invalid MQTT packet length.');
    }

    private static function read($socket, int $length): string
    {
        $result = '';
        while (strlen($result) < $length) {
            $chunk = @fread($socket, $length - strlen($result));
            if ($chunk === false || $chunk === '') {
                throw new RuntimeException('MQTT connection closed or timed out.');
            }
            $result .= $chunk;
        }
        return $result;
    }
}
