"""Run with: python3 -m unittest discover -s server/tests -v."""

from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest

SOURCE = Path(__file__).resolve().parents[1]
PHP = shutil.which('php')


def read_exact(connection: socket.socket, length: int) -> bytes:
    result = b''
    while len(result) < length:
        chunk = connection.recv(length - len(result))
        if not chunk:
            raise EOFError('Connection closed')
        result += chunk
    return result


def packet(connection: socket.socket) -> tuple[int, bytes]:
    header = read_exact(connection, 1)[0]
    length = 0
    multiplier = 1
    for _ in range(4):
        digit = read_exact(connection, 1)[0]
        length += (digit & 127) * multiplier
        if not digit & 128:
            return header, read_exact(connection, length)
        multiplier *= 128
    raise ValueError('Invalid remaining length')


@contextmanager
def broker(reject: bool = False):
    records = []
    errors = []
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(5)

        def serve() -> None:
            try:
                with listener.accept()[0] as connection:
                    connection.settimeout(5)
                    records.append(packet(connection))
                    connection.sendall(b'\x20\x02\x00' + (b'\x05' if reject else b'\x00'))
                    if reject:
                        return
                    records.append(packet(connection))
                    connection.sendall(b'\x40\x02\x00\x01')
                    records.append(packet(connection))
            except Exception as error:
                errors.append(error)

        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        yield listener.getsockname()[1], records
        worker.join(6)
        if worker.is_alive():
            raise AssertionError('Broker did not finish')
        if errors:
            raise errors[0]


@unittest.skipUnless(PHP, 'PHP CLI is required for HTTP/MQTT tests')
class BridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy(SOURCE / 'callback.php', self.root)
        shutil.copytree(SOURCE / 'lib', self.root / 'lib')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            self.port = listener.getsockname()[1]
        self.process = subprocess.Popen(
            [PHP, '-S', f'127.0.0.1:{self.port}', '-t', str(self.root)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        self.addCleanup(self.stop_server)
        for _ in range(100):
            try:
                with socket.create_connection(('127.0.0.1', self.port), timeout=0.1):
                    break
            except OSError:
                if self.process.poll() is not None:
                    self.fail('PHP server exited')
                time.sleep(0.02)
        else:
            self.fail('PHP server did not start')

    def stop_server(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=5)

    def configure(self, port: int) -> None:
        (self.root / 'config.php').write_text(
            "<?php return ['callback_token'=>'test-secret','mqtt'=>["
            f"'host'=>'127.0.0.1','port'=>{port},"
            "'username'=>'mqtt-user','password'=>'mqtt-password','timeout'=>1]];"
        )

    def request(self, body: bytes, method: str = 'POST') -> int:
        with http.client.HTTPConnection('127.0.0.1', self.port, timeout=5) as connection:
            connection.request(method, '/callback.php', body, {'Content-Type': 'application/json'})
            response = connection.getresponse()
            response.read()
            return response.status

    def test_original_json_and_qos_one(self) -> None:
        raw = b'{ "apikey": "test-secret", "data": [], "extra": "unchanged" }'
        with broker() as (port, records):
            self.configure(port)
            self.assertEqual(self.request(raw), 200)
        connect_header, connect = records[0]
        self.assertEqual(connect_header, 0x10)
        self.assertEqual(connect[:10], b'\x00\x04MQTT\x04\xc2\x00\x1e')
        self.assertIn(b'\x00\x09mqtt-user\x00\x0dmqtt-password', connect)
        self.assertEqual(records[1], (0x32, self.expected_publish(raw)))
        self.assertEqual(records[2], (0xE0, b''))

    @staticmethod
    def expected_publish(raw: bytes) -> bytes:
        topic = b'jeedom/raw/event'
        return len(topic).to_bytes(2, 'big') + topic + b'\x00\x01' + raw

    def test_rejected_broker(self) -> None:
        with broker(reject=True) as (port, records):
            self.configure(port)
            self.assertEqual(self.request(b'{"apikey":"test-secret","data":[]}'), 503)
        self.assertEqual(len(records), 1)

    def test_wrong_token(self) -> None:
        self.configure(1)
        self.assertEqual(self.request(b'{"apikey":"wrong","data":[]}'), 403)

    def test_invalid_json(self) -> None:
        self.configure(1)
        self.assertEqual(self.request(b'{'), 400)

    def test_missing_events(self) -> None:
        self.configure(1)
        self.assertEqual(self.request(b'{"apikey":"test-secret"}'), 400)

    def test_get_rejected(self) -> None:
        self.assertEqual(self.request(b'', 'GET'), 405)

    def test_large_payload(self) -> None:
        self.configure(1)
        self.assertEqual(self.request(b' ' * 1048577), 413)

    def test_broker_unavailable(self) -> None:
        self.configure(1)
        self.assertEqual(self.request(b'{"apikey":"test-secret","data":[]}'), 503)


    def test_debug_log_excludes_secrets_and_payload(self) -> None:
        with broker() as (port, records):
            self.configure(port)
            config = self.root / 'config.php'
            config.write_text(config.read_text().replace("'callback_token'", "'debug'=>true,'debug_log'=>__DIR__.'/bridge-debug.log','callback_token'"))
            self.assertEqual(self.request(b'{"apikey":"test-secret","data":[],"private":"private-event"}'), 200)
        log = (self.root / 'bridge-debug.log').read_text()
        entries = [json.loads(line) for line in log.splitlines()]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['mqtt'], 'ok')
        self.assertEqual(entries[0]['status'], 200)
        self.assertNotIn('test-secret', log)
        self.assertNotIn('mqtt-password', log)
        self.assertNotIn('private-event', log)

    def test_debug_disabled_by_default(self) -> None:
        self.configure(1)
        self.assertEqual(self.request(b'{"apikey":"wrong","data":[]}'), 403)
        self.assertFalse((self.root / 'bridge-debug.log').exists())


    def test_debug_events_includes_event_data_without_callback_key(self) -> None:
        with broker() as (port, records):
            self.configure(port)
            config = self.root / 'config.php'
            config.write_text(config.read_text().replace("'callback_token'", "'debug'=>true,'debug_events'=>true,'debug_log'=>__DIR__.'/bridge-debug.log','callback_token'"))
            self.assertEqual(self.request(b'{"apikey":"test-secret","data":[{"deviceName":"Motion","event":"armed"}]}'), 200)
        log = (self.root / 'bridge-debug.log').read_text()
        entries = [json.loads(line) for line in log.splitlines()]
        self.assertEqual(len(entries), 1)
        event = entries[0]
        self.assertEqual(event['mqtt'], 'ok')
        self.assertEqual(event['data'], [{'deviceName': 'Motion', 'event': 'armed'}])
        self.assertNotIn('test-secret', log)
        self.assertNotIn('apikey', log)


    def test_mqtt_error_is_one_line_with_event_data(self) -> None:
        self.configure(1)
        config = self.root / 'config.php'
        config.write_text(config.read_text().replace("'callback_token'", "'debug'=>true,'debug_events'=>true,'debug_log'=>__DIR__.'/bridge-debug.log','callback_token'"))
        self.assertEqual(self.request(b'{"apikey":"test-secret","data":[{"id":"device"}]}'), 503)
        entries = [json.loads(line) for line in (self.root / 'bridge-debug.log').read_text().splitlines()]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['mqtt'], 'error')
        self.assertEqual(entries[0]['data'], [{'id': 'device'}])
        self.assertIn('error', entries[0])


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination = self.root / 'site' / 'some-folder'
        self.destination.mkdir(parents=True)
        binary = self.root / 'bin'
        binary.mkdir()
        wget = binary / 'wget'
        wget.write_text(
            '#!/bin/sh\nset -eu\n'
            'file=${3##*/server/}\n'
            'if [ "${FAIL_DOWNLOAD:-}" = "$file" ]; then exit 1; fi\n'
            'cp "$BRIDGE_SOURCE/$file" "$2"\n'
        )
        wget.chmod(0o755)
        self.env = dict(os.environ, PATH=f'{binary}:{os.environ["PATH"]}', BRIDGE_SOURCE=str(SOURCE))

    def install(self) -> subprocess.CompletedProcess:
        return subprocess.run(['sh', str(SOURCE / 'install.sh')], cwd=self.destination, env=self.env, capture_output=True, text=True)

    def test_install_under_prefix(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual((self.destination / '.htaccess').read_bytes(), (SOURCE / '.htaccess').read_bytes())
        self.assertTrue((self.destination / 'lib/MqttPublisher.php').is_file())
        self.assertEqual((self.destination / 'config.php').read_bytes(), (SOURCE / 'config.example.php').read_bytes())

    def test_update_preserves_credentials(self) -> None:
        (self.destination / 'config.php').write_text('my existing settings')
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual((self.destination / 'config.php').read_text(), 'my existing settings')

    def test_download_failure_keeps_existing_files(self) -> None:
        (self.destination / 'callback.php').write_text('old handler')
        self.env['FAIL_DOWNLOAD'] = 'lib/MqttPublisher.php'
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual((self.destination / 'callback.php').read_text(), 'old handler')
        self.assertEqual(list(self.destination.glob('.ajax-bridge-install.*')), [])


if __name__ == '__main__':
    unittest.main()
