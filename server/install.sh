#!/bin/sh
set -eu

command -v wget >/dev/null 2>&1 || { echo 'wget is required.' >&2; exit 1; }
base='https://github.com/bob-tm/ha_ajax_security/raw/refs/heads/main/server'
staging=$(mktemp -d .ajax-bridge-install.XXXXXX)
trap 'rm -rf "$staging"' EXIT HUP INT TERM
mkdir -p "$staging/lib"
for file in callback.php config.example.php lib/MqttPublisher.php .htaccess README.md install.sh; do
    echo "Downloading $file"
    wget -qO "$staging/$file" "$base/$file"
done
mkdir -p lib
for file in callback.php config.example.php lib/MqttPublisher.php .htaccess README.md install.sh; do
    mv "$staging/$file" "$file"
done
if [ ! -e config.php ]; then
    cp config.example.php config.php
    chmod 640 config.php
    echo 'Created config.php. Edit the callback token and MQTT settings before use.'
else
    echo 'Kept your existing config.php.'
fi
touch bridge-debug.log
if ! chgrp www-data bridge-debug.log; then
    echo 'Warning: could not set the log group to www-data. Give your PHP service write access manually.' >&2
fi
chmod 660 bridge-debug.log
echo 'Installed. See README.md for Apache and Home Assistant setup.'
