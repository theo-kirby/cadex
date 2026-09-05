# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Harness discovery contracts. Run with Python; no Blender or credentials needed."""

import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch, MagicMock

# Load the pure modules without importing the application's bpy entry point.
_PACKAGE = '_cadex_harness_contract'
package = types.ModuleType(_PACKAGE)
package.__path__ = [str(Path(__file__).resolve().parents[2] / 'scripts/startup/mesh_agent')]
sys.modules[_PACKAGE] = package
harness = importlib.import_module(_PACKAGE + '.harness')
backend = importlib.import_module(_PACKAGE + '.backend')


class HarnessTests(unittest.TestCase):
    def test_codex_paginates_filters_and_reports_account(self):
        client = MagicMock()
        client.call.side_effect = [
            {}, {'account': {'type': 'chatgpt', 'email': 'person@example.test', 'planType': 'pro'}},
            {'data': [{'id': 'row1', 'model': 'fresh-model', 'displayName': 'Fresh'},
                      {'model': 'hidden', 'hidden': True}], 'nextCursor': 'page2'},
            {'data': [{'model': 'fresh-model'}, {'model': 'another-model'}]},
        ]
        with patch.object(harness, 'rpc') as rpc:
            rpc.return_value.__enter__.return_value = client
            account, models = harness._codex('/fake/codex')
        self.assertEqual(account, 'person@example.test · pro')
        self.assertEqual([row[0] for row in models], ['fresh-model', 'another-model'])
        self.assertEqual(client.call.call_args.args[0], 'model/list')
        self.assertEqual(client.call.call_args.args[1]['cursor'], 'page2')
        self.assertFalse(any('turn' in call.args[0] for call in client.call.call_args_list))

    def test_codex_signed_out_and_no_auth_provider_are_distinct(self):
        for required, expected in [(True, 'Not signed in'), (False, 'No login required')]:
            client = MagicMock()
            client.call.side_effect = [{}, {'account': None, 'requiresOpenaiAuth': required}, {'data': []}]
            with patch.object(harness, 'rpc') as rpc:
                rpc.return_value.__enter__.return_value = client
                self.assertEqual(harness._codex('/fake/codex')[0], expected)

    def test_claude_initialization_discovers_models_without_a_prompt(self):
        client = MagicMock()
        client.receive.return_value = {'response': {'subtype': 'success', 'request_id': 'init',
            'response': {'models': [{'value': 'future[1m]', 'displayName': 'Future'}]}}}
        status = types.SimpleNamespace(stdout=json.dumps({'loggedIn': True, 'email': 'person@example.test'}))
        with patch.object(harness, 'rpc') as rpc, patch.object(harness.subprocess, 'run', return_value=status):
            rpc.return_value.__enter__.return_value = client
            account, models = harness._claude('/fake/claude')
        self.assertEqual(account, 'person@example.test')
        self.assertEqual(models[0][0], 'future[1m]')
        self.assertEqual(client.send.call_args.args[0]['request'], {'subtype': 'initialize'})
        self.assertNotIn('prompt', client.send.call_args.args[0])

    def test_pi_provider_ids_and_only_display_metadata_escape(self):
        client = MagicMock()
        client.call.return_value = {'models': [{'provider': 'service', 'id': 'family/model', 'name': 'A model'}]}
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'auth.json').write_text(json.dumps({'service': {
                'type': 'oauth', 'accountId': 'account-123', 'access': 'SECRET', 'refresh': 'SECRET'}}))
            with patch.dict(os.environ, {'PI_CODING_AGENT_DIR': directory}), patch.object(harness, 'rpc') as rpc:
                rpc.return_value.__enter__.return_value = client
                result = harness._pi('/fake/pi')
        self.assertEqual(result[0], 'service: account-123')
        self.assertEqual(result[1][0][0], 'service/family/model')
        self.assertNotIn('SECRET', repr(result))

    def test_missing_cli_and_failed_discovery_have_no_fabricated_models(self):
        with patch.object(harness, 'binary', return_value=None):
            result = harness.discover('codex')
        self.assertEqual(result['models'], [])
        self.assertEqual(result['account'], 'Harness not installed')
        with patch.object(harness, 'binary', return_value='/fake/codex'), patch.object(
                harness, '_codex', side_effect=ValueError('SECRET')):
            result = harness.discover('codex')
        self.assertTrue(result['error'])
        self.assertEqual(result['models'], [])
        self.assertNotIn('SECRET', repr(result))

    def test_rpc_ignores_notifications_and_bounds_wait(self):
        process = types.SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO(
            'not json\n' + json.dumps({'method': 'status'}) + '\n' +
            json.dumps({'id': '1', 'result': {'data': []}}) + '\n'))
        client = harness.RPC(process)
        self.assertEqual(client.call('model/list'), {'data': []})
        with self.assertRaises(harness.DiscoveryError):
            client.call('account/read')  # EOF is an error, never an endless wait.
        client.lines = __import__('queue').Queue()
        client.deadline = 0
        with self.assertRaises(harness.DiscoveryError):
            client.receive(lambda m: True)

    def test_rpc_process_reaped_after_failure(self):
        process = MagicMock()
        process.stdout = io.StringIO('')
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('harness', 3), 0]
        with patch.object(harness.subprocess, 'Popen', return_value=process):
            with self.assertRaises(RuntimeError):
                with harness.rpc(['/fake/cli']):
                    raise RuntimeError('failed')
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        self.assertTrue(process.stdout.closed)

    def test_login_script_quotes_paths_and_signals_completion(self):
        executable = "/tmp/a path/cli'$(false)"
        with patch.object(harness, 'binary', return_value=executable), patch.object(
                harness.sys, 'platform', 'darwin'), patch.object(harness.subprocess, 'run') as run:
            directory = harness.login('codex')
        try:
            script = Path(directory.name, 'Sign in.command').read_text()
            self.assertIn(harness.shlex.join([executable, 'login']), script)
            self.assertIn('"$?"', script)
            self.assertEqual(run.call_args.args[0][:3], ['open', '-a', 'Terminal'])
        finally:
            directory.cleanup()

    def test_harness_default_omits_model_override_for_fresh_and_resume(self):
        for cls, path_key in [(backend.ClaudeCodeBackend, 'claude_path'),
                              (backend.CodexBackend, 'codex_path')]:
            instance = cls(**{path_key: '/fake/cli'}, model='', system_prompt='',
                           tool_names=[], bridge_port=1, bridge_token='test')
            try:
                for session in [None, 'session123']:
                    instance.session_id = session
                    command = instance._command('hello') if path_key == 'claude_path' else instance._command()
                    self.assertNotIn('--model', command)
                    instance.model = 'discovered-model'
                    command = instance._command('hello') if path_key == 'claude_path' else instance._command()
                    self.assertEqual(command[command.index('--model') + 1], 'discovered-model')
                    instance.model = ''
            finally:
                __import__('shutil').rmtree(instance._workdir)


if __name__ == '__main__':
    unittest.main()
