"""Offline proofs for source recovery and the baseline-only diagnostic."""
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import fixtures
import trial
from test_trial import AgentSandbox, START, approval


def diagnostic_approval():
    return dict(approval(), mode='baseline-only', injection=False, cases=[],
                deadline=(START + dt.timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                post_reboot_reconciled=True, residuals=dict(zombies=[], journals=[]))


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
