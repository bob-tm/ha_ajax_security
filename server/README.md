# Ajax callback → MQTT bridge

A small PHP endpoint replacing Jeedom's event forwarding. It checks the callback
API key and publishes the original JSON to `jeedom/raw/event`. Outgoing Ajax
requests stay in the Home Assistant integration through Jeedom Market.

## Requirements

- Apache 2.4 with PHP 7.4 or newer (PHP-FPM or mod_php).
- Apache `mod_rewrite` and `AllowOverride FileInfo` enabled for the installation folder.
- An HTTPS address reachable by the Jeedom cloud gateway.
- Network access from PHP to your existing MQTT broker.
- `wget` for installation only.

The MQTT client is included. No Composer, Git, framework, database, or running
Jeedom installation is needed. PHP's OpenSSL extension is needed if MQTT TLS is enabled.

## Install

Open a terminal on your web server and **change into your domain's installation
folder**, for example `domain/some-folder`. The folder must already exist:

```sh
cd /path/to/domain/some-folder
```

Then run this single command **inside that folder**:

```sh
wget -qO- https://github.com/bob-tm/ha_ajax_security/raw/refs/heads/main/server/install.sh | sh
```

Files are downloaded directly from the repository's `main` branch, without an
archive or release. The server files must be committed and pushed to GitHub first.
Run the same command to update; an existing `config.php` is preserved.
Existing bridge code and `.htaccess` in the current directory are replaced.
Use a dedicated folder, not the root of an existing application.

## Update

First commit and push your server changes to the `main` branch on GitHub.
Then connect to your web server and run:

```sh
cd /path/to/domain/some-folder
wget -qO- https://github.com/bob-tm/ha_ajax_security/raw/refs/heads/main/server/install.sh | sh
```

Replace the `cd` path with your installation directory if it differs.
The installer replaces the bridge files and preserves your existing `config.php`,
including MQTT credentials and the callback token. New configuration options
must be copied manually from `config.example.php` into `config.php`.

## Configure

Edit `config.php`, which the installer creates from `config.example.php`:

```php
return [
    'callback_token' => 'your-long-random-secret',
    'mqtt' => [
        'host' => '192.168.1.10',
        'port' => 1883,
        'username' => 'ajax_bridge',
        'password' => 'your-mqtt-password',
        'tls' => false,
        'timeout' => 5,
    ],
];
```

| Setting | Value |
| --- | --- |
| `callback_token` | A long random secret; enter the same value in HA's **Jeedom Ajax System plugin API key** field. |
| `mqtt.host` | MQTT broker hostname or IP, reachable from this web server. |
| `mqtt.port` | Broker port, usually `1883`, or `8883` with TLS. |
| `mqtt.username` | MQTT account username; empty if the broker allows anonymous access. |
| `mqtt.password` | MQTT account password; empty if none is required. |
| `mqtt.tls` | `true` for TLS with certificate verification, otherwise `false`. |
| `mqtt.timeout` | MQTT connection and socket timeout in seconds. |

The MQTT account must be allowed to publish to `jeedom/raw/event`.
Ensure PHP can read `config.php`. The installer sets mode `640`; adjust its owner
or group to match your PHP service if necessary. Keep credentials out of Git.

## Connect Home Assistant

For an installation at `https://example.com/some-folder`, enter:

- **Callback URL:** `https://example.com/some-folder`
- **Jeedom Ajax System plugin API key:** the value of `callback_token` in `config.php`

Complete the Market/Ajax sign-in again to register this callback address.
The gateway uses the compatible endpoint:

```text
https://example.com/some-folder/plugins/ajaxSystem/core/php/jeeAjaxSystem.php
```

The included `.htaccess` rewrites that path internally to `callback.php`, preserving
the POST body. The prefix can be any folder; no edits to `.htaccess` are needed.
The MQTT topic is unchanged, so the existing HA subscription keeps working.

Before stopping Jeedom, verify that an actual Ajax event arrives in HA through
this bridge. Callback registration is managed by the external gateway.

## Check delivery

From a terminal, replace the URL and token:

```sh
curl -i -X POST https://example.com/some-folder/plugins/ajaxSystem/core/php/jeeAjaxSystem.php \
  -H 'Content-Type: application/json' \
  --data '{"apikey":"your-long-random-secret","data":[]}'
```

Expect HTTP `200` and the JSON message `Event forwarded.`. The original JSON
should appear on `jeedom/raw/event`; an empty `data` array is a connectivity test.
Wrong tokens return `403`, invalid event JSON returns `400`, and MQTT failures
return `503`. PHP logs a generic delivery failure without credentials or payloads.

Publishing uses MQTT 3.1.1, QoS 1, and no retain. HTTP success is returned after the
broker acknowledges the publish. This confirms broker receipt, not HA processing.
There is no local queue; failed delivery returns an error to the caller. Whether
the cloud retries failed HTTP callbacks must be verified with the gateway.
QoS 1 can deliver duplicates.

The `.htaccess` also blocks HTTP access to configuration, library, and installer
files. Verify that requesting `config.php` returns `403` before using real secrets.

## Development checks

With PHP CLI and Python 3 available, run from the repository root:

```sh
php -l server/callback.php
php -l server/lib/MqttPublisher.php
php -l server/config.example.php
sh -n server/install.sh
python3 -m unittest discover -s server/tests -v
```

Tests use a local fake MQTT broker and PHP's development HTTP server. They do not
contact Ajax, Jeedom, or your real MQTT broker. Apache rewrite rules must be checked
on the deployment server using the compatible endpoint shown above.

## Debug logging

To enable debug logging, add or change these settings in `config.php`:

```php
'debug' => true,
'debug_log' => __DIR__ . '/bridge-debug.log',
```

These are top-level settings, alongside `callback_token` and `mqtt`. Older
configuration files are preserved by the installer, so add the settings manually
when updating. Debug logging is disabled by default.

The installer creates `bridge-debug.log`, attempts to set its group to `www-data`
without sudo, and sets mode `660`. If group assignment fails or PHP runs under a
different group, give that PHP service write access manually. Existing log contents
are preserved during updates. Follow requests with:

```sh
tail -f bridge-debug.log
```

Each callback produces one JSON log line, starting with the MQTT result and,
when `debug_events` is enabled, the event data:

```json
{"mqtt":"ok","data":[{"id":"device","updates":{}}],"time":"2026-01-01T12:00:00+00:00","status":200,"result":"Event forwarded.","duration_ms":12}
```

Failed delivery uses `"mqtt":"error"` and includes the failure reason in `error`.
Rejected requests also use `"mqtt":"error"`; their `status` and `result` explain
why publishing was not attempted. Only authenticated event data can be logged.
Credentials and the callback envelope's API key are excluded. There are no separate
receipt, authentication, or publication log lines.

Set `debug_log` to an absolute path outside the web folder if preferred, or to
`''` to use the standard PHP error log. The included `.htaccess` blocks HTTP access
to `.log` files; logs are also excluded from Git. If a configured log file cannot
be written, PHP's error log receives a warning and request handling continues.

Set `debug` back to `false` after troubleshooting. File logging appends entries
without automatic rotation; remove or rotate the log as needed.

### Include event data

To log the authenticated callback's `data` array, enable both options in
`config.php`:

```php
'debug' => true,
'debug_events' => true,
```

`debug_events` defaults to `false` and has no effect when `debug` is disabled.
Only the `data` array is logged; the callback envelope and its `apikey` are omitted.
Event data can contain device names, identifiers, and security activity. Disable
this option after debugging if those details should not remain in the log.
