"""Offline proofs for source recovery and the baseline-only diagnostic."""
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import select
import socket
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import Mock, patch

import fixtures
import trial
from test_trial import AgentSandbox, START, approval


def diagnostic_approval():
    return dict(approval(), mode='baseline-only', injection=False, cases=[],
                deadline=(START + dt.timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                post_reboot_reconciled=True, residuals=dict(zombies=[], journals=[]))


class DNSFixtureTests(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self, host='127.0.0.1', port=0):
        # Signal the actual CLI's ephemeral bind without adding a production API.
        program = '''import fixtures, socketserver
class Ready(socketserver.UDPServer):
    def server_activate(self):
        super().server_activate()
        fixtures.emit(self.server_address)
socketserver.UDPServer = Ready
fixtures.main()
'''
        process = subprocess.Popen([sys.executable, '-u', '-c', program, 'dns',
                                    '--host', host, '--port', str(port)],
                                   cwd=trial.HERE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertTrue(select.select([process.stdout], [], [], 5)[0], 'fixture startup timeout')
            line = process.stdout.readline()
            self.assertTrue(line, 'fixture exited before binding')
            address = json.loads(line)
            self.assertEqual(address[0], host)
            yield tuple(address)
            self.assertIsNone(process.poll(), 'fixture crashed')
        finally:
            process.terminate()
            try:
                _, error = process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                _, error = process.communicate(timeout=3)
            self.assertEqual(error, '')

    def probe(self, dig):
        def lookup(name, port, family=socket.AF_INET):
            if family == socket.AF_INET6: raise socket.gaierror('local NODATA')
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', port))]
        body = b'HTTP/1.0 200 OK\r\n\r\n' + json.dumps(dict(fixture='task', service='service.ld01.test')).encode()
        sock = Mock(recv=Mock(side_effect=[body, b'', body, b'']))
        context = Mock(__enter__=Mock(return_value=sock), __exit__=Mock(return_value=False))
        stderr = io.StringIO()
        with patch.object(fixtures.socket, 'getaddrinfo', side_effect=lookup), \
                patch.object(fixtures.socket, 'create_connection', return_value=context), \
                patch.object(fixtures.subprocess, 'run', side_effect=dig), \
                patch.object(fixtures, 'fresh', return_value=dict(seq=1, connection='direct')), \
                contextlib.redirect_stderr(stderr):
            result = fixtures.probe_report('baseline_probe', '127.0.0.1', '127.0.0.1')
        return result, stderr.getvalue()

    def saved_shape(self, command, *, authoritative=True, status='NOERROR', records=None, exit=0):
        if command[1] == '@127.0.0.11':
            return subprocess.CompletedProcess(command, 9, ';; no servers could be reached\n', '')
        name, kind = command[-2:]
        if records is None: records = [name + '. 0 IN A 127.0.0.1'] if kind == 'A' else []
        output = (';; Got answer:\n;; ->>HEADER<<- opcode: QUERY, status: ' + status + ', id: 1\n'
                  ';; flags: qr' + (' aa' if authoritative else '') + ' rd ra; QUERY: 1, ANSWER: ' +
                  str(len(records)) + ', AUTHORITY: 0, ADDITIONAL: 1\n\n'
                  ';; OPT PSEUDOSECTION:\n; EDNS: version: 0, flags:; udp: 1232\n' + '\n'.join(records) + '\n')
        return subprocess.CompletedProcess(command, exit, output, '')

    def test_saved_shape_reproduces_only_lab_aaaa_failure_at_original_stage(self):
        def replay(command, **kwargs):
            return self.saved_shape(command, authoritative=command[-1] == 'A')
        result, stderr = self.probe(replay)
        self.assertEqual(result['error'], dict(stage='validate-dns-baseline', type='ValueError',
                                              message='positive DNS/embedded rejection mismatch'))
        rows = result['partial']['dns']
        self.assertEqual([(r['protocol'], r['kind']) for r in rows
                          if r['positive'] != (r['resolver'] == '127.0.0.1')],
                         [('udp', 'AAAA'), ('tcp', 'AAAA')])
        self.assertFalse(any(r['responded'] for r in rows if r['resolver'] == '127.0.0.11'))
        self.assertIn('"stage": "validate-dns-baseline", "status": "failed"', stderr)

    def test_bad_baselines_still_fail_without_retry(self):
        changes = [('AAAA', dict(authoritative=False)), ('A', dict(records=[])),
                   ('A', dict(records=['x. 0 IN A 127.0.0.2'])),
                   ('A', dict(records=['x. 0 IN A 127.0.0.1', 'x. 0 IN A 127.0.0.2'])),
                   ('A', dict(records=['x. 0 IN CNAME service.ld01.test.', 'service.ld01.test. 0 IN A 127.0.0.1'])),
                   ('AAAA', dict(records=['x. 0 IN AAAA ::1'])),
                   ('AAAA', dict(status='NXDOMAIN')), ('A', dict(status='SERVFAIL')),
                   ('A', dict(exit=9))]
        for protocol in ('udp', 'tcp'):
            for kind, change in changes:
                with self.subTest(protocol=protocol, kind=kind, change=change):
                    calls = []
                    def dig(command, **kwargs):
                        calls.append(command)
                        target = (command[1] == '@127.0.0.1' and command[-1] == kind and
                                  ('+tcp' in command) == (protocol == 'tcp'))
                        return self.saved_shape(command, **(change if target else {}))
                    result, _ = self.probe(dig)
                    self.assertEqual(result['error']['stage'], 'validate-dns-baseline')
                    self.assertEqual(len(calls), 8)
            for positive in (False, True):
                with self.subTest(protocol=protocol, embedded_positive=positive):
                    def embedded(command, **kwargs):
                        if command[1] == '@127.0.0.11' and ('+tcp' in command) == (protocol == 'tcp'):
                            # Even a negative REFUSED reply violates embedded containment.
                            lab_command = [command[0], '@127.0.0.1', *command[2:]]
                            return self.saved_shape(lab_command, status='NOERROR' if positive else 'REFUSED')
                        return self.saved_shape(command)
                    result, _ = self.probe(embedded)
                    self.assertEqual(result['error']['stage'], 'validate-dns-baseline')

    def test_real_udp_tcp_dig_passes_unchanged_probe_with_unique_labels(self):
        real_run = subprocess.run
        queries = []
        with self.fixture() as (host, port):
            def dig(command, **kwargs):
                queries.append(command)
                if command[1] == '@127.0.0.11': return self.saved_shape(command)
                # Only redirect the destination port to our disposable loopback fixture.
                return real_run([*command[:2], '-p', str(port), *command[2:]], **kwargs)
            result, _ = self.probe(dig)
            self.assertNotIn('error', result, result)
            self.assertEqual(result['http'], result['named_http'])
            self.assertEqual(len({command[-2] for command in queries}), 8)
            lab = [row for row in result['dns'] if row['resolver'] == host]
            self.assertEqual({(r['protocol'], r['kind']) for r in lab},
                             {('udp', 'A'), ('udp', 'AAAA'), ('tcp', 'A'), ('tcp', 'AAAA')})
            self.assertTrue(all(r['positive'] for r in lab))
            for protocol in ('udp', 'tcp'):
                answer = real_run(['dig', '@' + host, '-p', str(port), '+time=1', '+tries=1',
                                   '+noall', '+comments', '+answer', '+authority',
                                   *(['+tcp'] if protocol == 'tcp' else []),
                                   uuid.uuid4().hex + '.ld01.test', 'AAAA'],
                                  capture_output=True, text=True, timeout=3)
                self.assertEqual(answer.returncode, 0, answer)
                self.assertIn('status: NOERROR', answer.stdout)
                self.assertIn('flags: qr aa rd;', answer.stdout)
                self.assertIn('ANSWER: 0, AUTHORITY: 1', answer.stdout)
                self.assertIn('SOA\tns.ld01.test. hostmaster.ld01.test.', answer.stdout)

    def question(self, name='fresh.ld01.test', kind=1, klass=1):
        wire = b''.join(bytes([len(label)]) + label.encode() for label in name.split('.')) + b'\0'
        return struct.pack('!6H', 1234, 0x0100, 1, 0, 0, 0) + wire + struct.pack('!HH', kind, klass)

    def exchange(self, address, packet, protocol):
        with socket.socket(type=socket.SOCK_DGRAM if protocol == 'udp' else socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            sock.connect(address)
            if protocol == 'udp':
                sock.send(packet)
                return sock.recv(1024)
            sock.sendall(struct.pack('!H', len(packet)) + packet)
            data = b''
            while chunk := sock.recv(1024): data += chunk
            self.assertEqual(struct.unpack('!H', data[:2])[0], len(data) - 2)
            return data[2:]

    def test_wire_exact_a_nodata_and_refusal_without_resolver(self):
        with self.fixture(host='127.0.0.2') as address:
            for protocol in ('udp', 'tcp'):
                for name in ('service.ld01.test', uuid.uuid4().hex + '.LD01.TeSt', 'a.b.ld01.test'):
                    for kind in (1, 28):
                        with self.subTest(protocol=protocol, name=name, kind=kind):
                            query = self.question(name, kind)
                            reply = self.exchange(address, query, protocol)
                            self.assertEqual(struct.unpack('!6H', reply[:12]),
                                             (1234, 0x8500, 1, int(kind == 1), int(kind == 28), 0))
                            self.assertEqual(reply[12:len(query)], query[12:])
                            if kind == 1:
                                self.assertEqual(struct.unpack('!HHIH', reply[-14:-4]), (1, 1, 0, 4))
                                self.assertEqual(reply[-4:], socket.inet_aton(address[0]))
                for name, kind, klass in [('example.invalid', 1, 1), ('ld01.test', 1, 1),
                                           ('a.ld01.test.invalid', 1, 1), ('a.notld01.test', 1, 1),
                                           ('a.ld01.test', 1, 3), ('a.ld01.test', 15, 1)]:
                    reply = self.exchange(address, self.question(name, kind, klass), protocol)
                    self.assertEqual(struct.unpack('!6H', reply[:12]), (1234, 0x8105, 1, 0, 0, 0))

    def test_edns_gets_minimal_opt_and_plain_replies_have_no_opt(self):
        with self.fixture() as address:
            for protocol in ('udp', 'tcp'):
                for name, kind in [('fresh.ld01.test', 1), ('fresh.ld01.test', 28), ('example.invalid', 1)]:
                    query = self.question(name, kind)
                    plain = self.exchange(address, query, protocol)
                    self.assertEqual(struct.unpack('!H', plain[10:12])[0], 0)
                    for flags in (0, 0x8000):
                        with self.subTest(protocol=protocol, name=name, kind=kind, flags=flags):
                            cookie = struct.pack('!HH', 10, 8) + b'12345678'
                            opt = b'\0' + struct.pack('!HHIH', 41, 1232, flags, len(cookie)) + cookie
                            edns = struct.pack('!6H', 1234, 0x0100, 1, 0, 0, 1) + query[12:] + opt
                            reply = self.exchange(address, edns, protocol)
                            self.assertEqual(reply[:10], plain[:10])
                            self.assertEqual(struct.unpack('!H', reply[10:12])[0], 1)
                            self.assertEqual(reply[12:-11], plain[12:])
                            self.assertEqual(reply[-11:], b'\0' + struct.pack('!HHIH', 41, 512, flags, 0))
                            self.assertLessEqual(len(reply), 512)

    def test_incomplete_tcp_does_not_block_healthy_udp_or_tcp(self):
        with self.fixture() as address, socket.create_connection(address, timeout=3) as incomplete:
            incomplete.sendall(b'\0')
            time.sleep(.1)  # Let the accepted request enter its incomplete frame read.
            for protocol in ('udp', 'tcp'):
                start = time.monotonic()
                reply = self.exchange(address, self.question(), protocol)
                self.assertLess(time.monotonic() - start, 1)
                self.assertEqual(struct.unpack('!6H', reply[:12]), (1234, 0x8500, 1, 1, 0, 0))
            incomplete.settimeout(.05)
            with self.assertRaises(socket.timeout): incomplete.recv(1)

    def test_restart_rebinds_same_loopback_port_after_completed_tcp_query(self):
        with self.fixture() as address:
            self.assertEqual(struct.unpack('!6H', self.exchange(address, self.question(), 'tcp')[:12]),
                             (1234, 0x8500, 1, 1, 0, 0))
        with self.fixture(host=address[0], port=address[1]) as restarted:
            self.assertEqual(restarted, address)
            for protocol in ('udp', 'tcp'):
                self.assertEqual(struct.unpack('!6H', self.exchange(restarted, self.question(), protocol)[:12]),
                                 (1234, 0x8500, 1, 1, 0, 0))

    def test_absolute_deadline_limits_paced_frames_and_allows_delayed_valid_fragmentation(self):
        with self.fixture() as address:
            with socket.create_connection(address, timeout=3) as sock:
                start = time.monotonic()
                sock.sendall(b'\0\x40')
                # Progress every .4s would keep a per-read two-second timeout alive.
                for _ in range(7):
                    if select.select([sock], [], [], .4)[0]:
                        self.assertEqual(sock.recv(1), b'')
                        break
                    sock.sendall(b'x')
                else:
                    self.fail('paced incomplete frame exceeded absolute deadline')
                self.assertLess(time.monotonic() - start, 2.8)
            for protocol in ('udp', 'tcp'):
                self.assertEqual(struct.unpack('!6H', self.exchange(address, self.question(), protocol)[:12]),
                                 (1234, 0x8500, 1, 1, 0, 0))
            with socket.create_connection(address, timeout=3) as sock:
                query = self.question()
                frame = struct.pack('!H', len(query)) + query
                sock.sendall(frame[:1])
                time.sleep(.15)
                sock.sendall(frame[1:10])
                time.sleep(.15)
                sock.sendall(frame[10:])
                data = b''
                while chunk := sock.recv(1024): data += chunk
                self.assertEqual(struct.unpack('!H', data[:2])[0], len(data) - 2)
                self.assertEqual(struct.unpack('!6H', data[2:14]), (1234, 0x8500, 1, 1, 0, 0))
            for protocol in ('udp', 'tcp'):
                self.assertEqual(struct.unpack('!6H', self.exchange(address, self.question(), protocol)[:12]),
                                 (1234, 0x8500, 1, 1, 0, 0))

    def test_malformed_datagrams_and_frames_are_bounded_and_service_survives(self):
        query = self.question()
        malformed = [b'', query[:11], query[:-1], query + b'x', b'x' * 513,
                     query[:12] + b'\xc0\x0c' + query[-4:],
                     query[:12] + b'\x40' + b'x' * 64 + b'\0' + query[-4:],
                     self.question('.'.join(['a' * 63] * 4) + '.ld01.test')]
        for field, value in ((1, 0x8100), (1, 0x0900), (1, 0x0300), (1, 0x0140),
                             (2, 0), (2, 2), (3, 1), (4, 1), (5, 2)):
            header = [1234, 0x0100, 1, 0, 0, 0]
            header[field] = value
            malformed.append(struct.pack('!6H', *header) + query[12:])
        edns = struct.pack('!6H', 1234, 0x0100, 1, 0, 0, 1) + query[12:]
        malformed += [edns, edns + b'\0\0)\x04\xd0\0\0\0\0\0\x04' + b'\0\x0a\0\x08',
                      edns + b'\0\0)\x04\xd0\0\0\0\0\0\x01x',
                      edns + b'\0\0)\x04\xd0\0\x01\0\0\0\0']
        with self.fixture() as address:
            for packet in malformed:
                with self.subTest(packet=packet[:20]):
                    with socket.socket(type=socket.SOCK_DGRAM) as sock:
                        sock.settimeout(.05)
                        sock.sendto(packet, address)
                        with self.assertRaises(socket.timeout): sock.recv(1024)
                    with socket.create_connection(address, timeout=3) as sock:
                        sock.sendall(struct.pack('!H', len(packet)) + packet)
                        sock.shutdown(socket.SHUT_WR)
                        self.assertEqual(sock.recv(1024), b'')
            for frame in (b'\0', b'\0\0', b'\x02\x01', b'\xff\xff', b'\0\x20short'):
                with socket.create_connection(address, timeout=3) as sock:
                    sock.sendall(frame)
                    sock.shutdown(socket.SHUT_WR)
                    self.assertEqual(sock.recv(1024), b'')
            # An unfinished frame cannot keep its worker alive forever.
            with socket.create_connection(address, timeout=3) as sock:
                start = time.monotonic()
                sock.sendall(b'\0')
                self.assertEqual(sock.recv(1024), b'')
                self.assertLess(time.monotonic() - start, 3)
            for protocol in ('udp', 'tcp'):
                self.assertEqual(struct.unpack('!6H', self.exchange(address, query, protocol)[:12]),
                                 (1234, 0x8500, 1, 1, 0, 0))
            with socket.create_connection(address, timeout=3) as sock:
                frame = struct.pack('!H', len(query)) + query
                for byte in frame: sock.sendall(bytes([byte]))
                data = b''
                while chunk := sock.recv(1024): data += chunk
                self.assertEqual(struct.unpack('!H', data[:2])[0], len(data) - 2)
                self.assertEqual(struct.unpack('!6H', data[2:14]), (1234, 0x8500, 1, 1, 0, 0))

    def test_server_unit_uses_fixture_on_tunnel_only_and_preserves_lifecycle(self):
        text = (trial.HERE / 'setup-server.sh').read_text()
        self.assertIn('dns) command="/usr/bin/python3 $root/fixtures.py dns --host $server --port 53"; after="$prefix-vpn.service"', text)
        self.assertNotIn('cat > dns.conf', text)
        self.assertNotIn('/usr/sbin/dnsmasq --keep-in-foreground', text)
        self.assertIn('for binary in openvpn dnsmasq openssl python3;', text)
        self.assertIn('RuntimeMaxSec=$remaining', text)
        self.assertIn('for service in http dns heartbeat vpnheartbeat;', text)

    def test_server_metadata_identifies_active_dns_python_and_retained_package_versions(self):
        text = (trial.HERE / 'setup-server.sh').read_text()
        code = text.split("<<'PY' > server.json\n", 1)[1].split('\nPY', 1)[0]
        versions = {('openvpn', '--version'): 'OpenVPN retained\n',
                    ('dnsmasq', '--version'): 'Dnsmasq retained\n',
                    ('/usr/bin/python3', '--version'): 'Python active\n'}
        output = io.StringIO()
        with patch.object(sys, 'argv', ['-', 'task', '10.231.0.0/24', '10.231.0.1', 'deadline']), \
                patch.object(subprocess, 'check_output', side_effect=lambda command, **kw: versions[tuple(command)]), \
                contextlib.redirect_stdout(output):
            exec(compile(code, 'server-metadata', 'exec'), {})
        result = json.loads(output.getvalue())
        self.assertEqual(result['dns_backend'], 'fixtures.py:dns')
        self.assertEqual(result['python_executable'], '/usr/bin/python3')
        self.assertEqual(result['python'], 'Python active')
        self.assertEqual(result['dnsmasq'], 'Dnsmasq retained')
        self.assertEqual(result['openvpn'], 'OpenVPN retained')


class BaselineTests(unittest.TestCase):
    def test_authority_is_separate_from_fault_campaign_and_never_requests_injection(self):
        value = diagnostic_approval()
        self.assertEqual(trial.authorize(value, START, baseline_only=True), value)
        with self.assertRaises(ValueError): trial.authorize(value, START)
        with self.assertRaises(ValueError): trial.authorize(approval(), START, baseline_only=True)
        for change in (dict(injection=True), dict(cases=['F1']), dict(post_reboot_reconciled=False),
                       dict(deadline=(START + dt.timedelta(minutes=31)).strftime('%Y-%m-%dT%H:%M:%SZ'))):
            with self.subTest(change=change), self.assertRaises(ValueError):
                trial.authorize(dict(value, **change), START, baseline_only=True)

    def test_agent_allows_diagnostic_prepare_but_rejects_client_injection_before_signal(self):
        with tempfile.TemporaryDirectory() as directory:
            s = AgentSandbox(directory)
            (s.root / 'authorization.json').write_text(json.dumps(diagnostic_approval()))
            s.prepare()
            self.assertEqual(s.ns['phase']()['phase'], 'starting')
            with patch.object(s.ns['os'], 'kill') as kill:
                with self.assertRaisesRegex(RuntimeError, 'prohibited'):
                    s.ns['kill_client'](s.generation)
                kill.assert_not_called()
            s.restore()

    def test_baseline_is_one_connect_off_without_cycle_reconnect_or_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            c = trial.Trial(Path(directory), diagnostic_approval())
            c.capture_process = Mock(wait=Mock(return_value=0))
            events = []
            def capture(): c.state['capture'] = {}; events.append('capture')
            with patch.object(c, 'start_capture', side_effect=capture), \
                    patch.object(c, 'connect', side_effect=lambda _: events.append('connect')), \
                    patch.object(c, 'off', side_effect=lambda _: events.append('off')), \
                    patch.object(c, 'capture_ready'), patch.object(trial, 'stop_capture', return_value={}), \
                    patch.object(c, 'cycle') as cycle, patch.object(trial, 'agent') as agent, \
                    patch.object(trial, 'stop_forward') as stop:
                c.baseline()
                self.assertEqual(events, ['capture', 'connect', 'off'])
                cycle.assert_not_called(); agent.assert_not_called(); stop.assert_not_called()
            self.assertEqual(c.evidence['cycles'][0]['status'], 'PASS')
            self.assertNotIn('injected_at', c.evidence['cycles'][0])
            with patch.object(c, 'start_capture') as capture:
                with self.assertRaisesRegex(ValueError, 'prohibited'): c.cycle(0)
                capture.assert_not_called()

    def test_failed_baseline_never_reconnects_or_injects_and_preserves_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            c = trial.Trial(Path(directory), diagnostic_approval())
            with patch.object(c, 'start_capture'), patch.object(c, 'connect', side_effect=ValueError('probe failed')), \
                    patch.object(c, 'off') as off, patch.object(c, 'cycle') as cycle:
                with self.assertRaisesRegex(ValueError, 'probe failed'): c.baseline()
                off.assert_not_called(); cycle.assert_not_called()
            self.assertEqual(c.evidence['cycles'][0]['status'], 'FAIL')

    def test_execute_dispatches_only_baseline_with_original_final_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            c = trial.Trial(Path(directory), diagnostic_approval())
            c.objects = []
            c.state.update(a_bridge='172.16.0.1', b_bridge='172.16.0.17')
            trial.private_write(Path(directory) / 'supervisor-ready.json', '{}')
            supervisor = Mock(poll=Mock(return_value=None), wait=Mock(return_value=0))
            with patch.object(c, 'preflight'), patch.object(c, 'deploy'), patch.object(c, 'forward'), \
                    patch.object(c, 'start_hold'), patch.object(c, 'prepare'), patch.object(c, 'finish_holds'), \
                    patch.object(c, 'baseline') as baseline, patch.object(c, 'cycle') as cycle, \
                    patch.object(trial.subprocess, 'Popen', return_value=supervisor), \
                    patch.object(trial, 'snapshot', return_value={}), patch.object(trial, 'run', return_value='[]'), \
                    patch.object(trial, 'inside', return_value='synthetic process table'), \
                    patch.object(trial, 'cleanup', return_value=[]) as cleanup:
                self.assertEqual(c.execute(), 'PASS', c.evidence.get('error'))
                baseline.assert_called_once(); cycle.assert_not_called()
                cleanup.assert_called_once_with(c.state, explicit_off='campaign completion')

    def test_missing_reboot_metadata_blocks_before_any_external_command(self):
        with tempfile.TemporaryDirectory() as directory:
            value = dict(diagnostic_approval(), baseline_dir=directory, retained_metadata=directory+'/missing.json')
            c = trial.Trial(Path(directory), value)
            with patch.object(trial, 'reserve'), patch.object(trial, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'metadata'): c.preflight()
                run.assert_not_called()

    def test_diagnostic_metadata_uses_new_baseline_name_and_private_files(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            value = dict(diagnostic_approval(), baseline_dir=directory, retained_metadata=str(p/'retained.json'))
            for name in ('resources.json', 'image.json', 'retained.json', 'baseline.json'):
                trial.private_write(p/name, '{}')
            self.assertEqual(trial.diagnostic_inputs(value), p)
            (p/'baseline.json').chmod(0o644)
            with self.assertRaisesRegex(ValueError, 'non-private'): trial.diagnostic_inputs(value)
            (p/'baseline.json').chmod(0o600)
            (p/'baseline.json').write_text('not json')
            with self.assertRaises(json.JSONDecodeError): trial.diagnostic_inputs(value)

    def test_reconciled_residuals_are_explicit_and_not_a_stale_pid_allowlist(self):
        zombie = dict(pid=1923, comm='python3', state='Z', identity='recorded-start')
        journal = dict(path='/run/ld01-cvpnrecorded', files={'cleanup.json': 'digest'})
        for expected, observed, valid in (
            (dict(zombies=[], journals=[]), dict(zombies=[], journals=[]), True),
            (dict(zombies=[zombie], journals=[journal]), dict(zombies=[zombie], journals=[journal]), True),
            (dict(zombies=[zombie], journals=[]), dict(zombies=[dict(zombie, identity='reused-pid')], journals=[]), False),
            (dict(zombies=[], journals=[]), dict(zombies=[], journals=[journal]), False),
        ):
            with self.subTest(expected=expected, observed=observed):
                data = dict(processes=observed['zombies'], journals=observed['journals'], unresolved=[])
                with patch.object(trial, 'inside', side_effect=lambda *a, **k: json.dumps(data) if 'python3' in a else ''):
                    if valid: trial.check_idle_a(expected)
                    else:
                        with self.assertRaisesRegex(ValueError, 'drift'): trial.check_idle_a(expected)
        with patch.object(trial, 'inside', return_value=json.dumps(dict(processes=[],journals=[],unresolved=['retained']))):
            with self.assertRaisesRegex(ValueError, 'unresolved'): trial.check_idle_a(dict(zombies=[],journals=[]))

    def test_worker_stage_error_and_partial_results_survive_without_killing_shell(self):
        program = "ns={'__name__':'diagnostic-worker'}; exec(compile(" + repr(Path(fixtures.__file__).read_text()) + ", 'fixtures', 'exec'),ns)\n"
        program += "def fail(server,direct,connected,stage,result):\n result['application']=['synthetic-answer']; stage('dns-lab-tcp-A'); raise ValueError('synthetic private error')\n"
        program += "ns['probes']=fail; ns['shell']()\n"
        real_popen = subprocess.Popen
        with tempfile.TemporaryDirectory() as directory:
            state = dict(private=directory)
            def launch(_command, **kwargs): return real_popen([sys.executable, '-u', '-c', program], **kwargs)
            with trial.lifecycle(state), patch.object(trial.subprocess, 'Popen', side_effect=launch):
                shell = trial.Shell()
            try:
                first = shell.request('identity')['identity']
                with self.assertRaisesRegex(ValueError, 'dns-lab-tcp-A') as caught:
                    shell.request('baseline_probe', server='10.231.0.1', direct='172.16.0.1')
                self.assertNotIn('synthetic private error', str(caught.exception))
                self.assertEqual(shell.request('identity')['identity'], first)
                record = json.loads(next(Path(directory).glob('shell-probe-*.json')).read_text())
                self.assertEqual(record['result']['partial']['application'], ['synthetic-answer'])
                self.assertEqual(record['result']['error']['stage'], 'dns-lab-tcp-A')
                text = shell.stderr_path.read_text()
                self.assertIn('synthetic private error', text)
                self.assertIn('"status": "failed"', text)
                self.assertEqual(shell.stderr_path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(next(Path(directory).glob('shell-probe-*.json')).stat().st_mode & 0o777, 0o600)
            finally: shell.close()

    def test_probe_report_records_precise_failure_stage_and_partial_data(self):
        def failure(*args, stage, result):
            result['dns'] = ['partial']
            stage('validate-dns-baseline')
            raise RuntimeError('synthetic failure')
        stderr = io.StringIO()
        with patch.object(fixtures, 'probes', side_effect=failure), contextlib.redirect_stderr(stderr):
            result = fixtures.probe_report('baseline_probe', '10.231.0.1', '172.16.0.1')
        self.assertEqual(result['error']['stage'], 'validate-dns-baseline')
        self.assertEqual(result['partial'], dict(dns=['partial']))
        self.assertIn('Traceback', stderr.getvalue())

    def test_server_authorization_block_accepts_only_matching_diagnostic_scope(self):
        text = (trial.HERE / 'setup-server.sh').read_text()
        code = text.split("<<'PY'\n",1)[1].split('\nPY',1)[0]
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'approval.json'
            for value, valid in ((diagnostic_approval(),True),(dict(diagnostic_approval(), injection=True),False)):
                p.write_text(json.dumps(value))
                # Rollback bypasses current time only; mode/window/scope checks remain real.
                result = subprocess.run([sys.executable, '-c', code, str(p), value['deadline'], 'rollback'],
                                        capture_output=True, text=True, timeout=3)
                self.assertEqual(result.returncode == 0, valid)


if __name__ == '__main__':
    unittest.main()
