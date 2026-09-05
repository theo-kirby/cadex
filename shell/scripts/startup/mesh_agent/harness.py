# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Account and model discovery through the installed agent CLIs, without turns.

No bpy, credentials copied into preferences, or product-owned model catalog.
Call from a worker: each RPC process has a deadline and is reaped on exit.
"""

import json
import os
import queue
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager

from . import backend

MODEL_PROPERTIES = {'claude': 'model', 'codex': 'codex_model', 'pi': 'pi_model'}


def binary(provider, path=''):
    return {'claude': backend.find_claude, 'codex': backend.find_codex,
            'pi': backend.find_pi}[provider](path)


def environment(executable):
    # npm's /usr/bin/env node must resolve next to the selected CLI in a GUI.
    env = dict(os.environ)
    env['PATH'] = os.path.dirname(executable) + os.pathsep + env.get('PATH', '')
    return env


class DiscoveryError(RuntimeError):
    pass


class RPC:
    def __init__(self, process, timeout=30):
        self.process = process
        self.deadline = time.monotonic() + timeout
        self.lines = queue.Queue()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        self.sequence = 0

    def _read(self):
        try:
            for line in self.process.stdout:
                try:
                    self.lines.put(json.loads(line))
                except ValueError:
                    pass
        finally:
            self.lines.put(None)

    def send(self, message):
        self.process.stdin.write(json.dumps(message) + '\n')
        self.process.stdin.flush()

    def receive(self, predicate):
        while True:
            try:
                message = self.lines.get(timeout=max(0, self.deadline - time.monotonic()))
            except queue.Empty:
                raise DiscoveryError('Harness did not respond. Refresh to retry.') from None
            if message is None:
                raise DiscoveryError('Harness exited during discovery. Check its installation and login.')
            if predicate(message):
                return message

    def call(self, method, params=None, pi=False):
        self.sequence += 1
        ident = str(self.sequence)
        self.send({'id': ident, 'type': method} if pi else
                  {'id': ident, 'method': method, 'params': params or {}})
        message = self.receive(lambda m: m.get('id') == ident)
        if message.get('error') or message.get('success') is False:
            # Arbitrary CLI errors can contain credentials; never surface raw output.
            raise DiscoveryError('Harness rejected ' + method + '. Update the CLI or sign in again.')
        return message.get('data' if pi else 'result') or {}


@contextmanager
def rpc(command):
    with tempfile.TemporaryDirectory(prefix='cadex_discovery_') as cwd:
        process = subprocess.Popen(command, cwd=cwd, env=environment(command[0]),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True)
        client = RPC(process)
        try:
            yield client
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            client.reader.join(timeout=1)
            process.stdin.close()
            process.stdout.close()


def _models(rows, provider):
    result, seen = [], set()
    for row in rows:
        if row.get('hidden'):
            continue
        ident = row.get('value') if provider == 'claude' else row.get('model', row.get('id'))
        if provider == 'pi':
            ident = row['provider'] + '/' + row['id']
        if not isinstance(ident, str) or not ident or ident in seen:
            continue
        seen.add(ident)
        label = row.get('displayName') or row.get('display_name') or row.get('name') or ident
        if provider == 'pi':
            label = row['provider'] + ' / ' + label
        result.append((ident, label, row.get('description') or ident))
    return result


def _codex(executable):
    with rpc([executable, 'app-server']) as client:
        client.call('initialize', {'clientInfo': {'name': 'cadex', 'version': '1'}})
        client.send({'method': 'initialized'})
        auth = client.call('account/read', {'refreshToken': False})
        account = auth.get('account')
        if account:
            label = account.get('email') or account.get('type') or 'Signed in'
            if account.get('planType'):
                label += ' · ' + account['planType']
        else:
            label = 'Not signed in' if auth.get('requiresOpenaiAuth', True) else 'No login required'
        rows, cursor, cursors = [], None, set()
        while True:
            page = client.call('model/list', {'limit': 100, 'includeHidden': False, 'cursor': cursor})
            rows.extend(page.get('data', []))
            cursor = page.get('nextCursor')
            if not cursor:
                break
            if cursor in cursors:
                raise DiscoveryError('Harness returned a repeated model page. Update the CLI.')
            cursors.add(cursor)
        return label, _models(rows, 'codex')


def _claude(executable):
    # SDK initialize returns the same model menu as Claude Code, without a prompt.
    command = [executable, '-p', '--input-format', 'stream-json',
               '--output-format', 'stream-json', '--verbose',
               '--no-session-persistence', '--strict-mcp-config',
               '--mcp-config', '{"mcpServers":{}}',
               '--settings', '{"disableAllHooks":true}']
    with rpc(command) as client:
        client.send({'type': 'control_request', 'request_id': 'init',
                     'request': {'subtype': 'initialize'}})
        message = client.receive(lambda m: m.get('type') == 'control_response'
                                 and m.get('response', {}).get('request_id') == 'init')
        response = message['response']
        if response.get('subtype') == 'error':
            raise DiscoveryError('Claude initialization failed. Update the CLI or sign in again.')
        data = response.get('response', {})
        models = _models(data.get('models', []), 'claude')
    status = subprocess.run([executable, 'auth', 'status', '--json'],
                            capture_output=True, text=True, timeout=15,
                            env=environment(executable))
    auth = json.loads(status.stdout)
    label = 'Not signed in'
    if auth.get('loggedIn'):
        label = auth.get('email') or auth.get('authMethod') or 'Signed in (account not reported)'
        if auth.get('subscriptionType'):
            label += ' · ' + auth['subscriptionType']
    return label, models


def _pi(executable):
    with rpc([executable, '--mode', 'rpc', '--no-session', '--no-extensions',
              '--no-skills', '--no-context-files', '--no-prompt-templates', '--no-themes']) as client:
        data = client.call('get_available_models', pi=True)
        models = _models(data.get('models', []), 'pi')
    # pi has multiple provider accounts. Its RPC exposes usable models but no
    # account endpoint. Read only display metadata; never decode or return tokens.
    directory = os.environ.get('PI_CODING_AGENT_DIR', os.path.expanduser('~/.pi/agent'))
    try:
        with open(os.path.join(directory, 'auth.json'), encoding='utf-8') as handle:
            accounts = json.load(handle)
    except (OSError, ValueError):
        accounts = {}
    labels = []
    for provider in sorted({ident.split('/', 1)[0] for ident, _, _ in models}):
        account = accounts.get(provider, {})
        identity = account.get('email') or account.get('accountId')
        method = {'api_key': 'API key (identity not reported)',
                  'oauth': 'OAuth (identity not reported)'}.get(
                      account.get('type'), 'Configured credentials (identity not reported)')
        labels.append(provider + ': ' + (identity or method))
    return '\n'.join(labels) or 'No authenticated providers', models


def discover(provider, path=''):
    executable = binary(provider, path)
    if not executable:
        return {'account': 'Harness not installed', 'models': [],
                'error': 'Install ' + provider + ' or set its CLI path in Settings > AI.'}
    try:
        account, models = {'claude': _claude, 'codex': _codex, 'pi': _pi}[provider](executable)
        return {'account': account, 'models': models,
                'error': '' if models else 'No models reported. Sign in and refresh.'}
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            subprocess.SubprocessError, DiscoveryError):
        return {'account': 'Account unavailable', 'models': [],
                'error': 'Could not query ' + provider + '. Check its installation and login, then refresh.'}


def login_command(provider, executable):
    args = {'claude': ['auth', 'login'], 'codex': ['login'], 'pi': []}[provider]
    return [executable, *args]


def login(provider, path=''):
    """Open the harness's own login UI. The returned directory signals completion.

    Keeping OAuth in the CLI also supports pi's provider chooser and browser
    fallback codes. No credentials pass through Cadex. The UI polls `done`.
    """
    executable = binary(provider, path)
    if not executable:
        raise DiscoveryError('Install ' + provider + ' or set its CLI path first.')
    if sys.platform != 'darwin':
        raise DiscoveryError('Open a terminal and run: ' + shlex.join(login_command(provider, executable)))
    directory = tempfile.TemporaryDirectory(prefix='cadex_login_')
    script = os.path.join(directory.name, 'Sign in.command')
    done = os.path.join(directory.name, 'done')
    with open(script, 'w', encoding='utf-8') as handle:
        handle.write('#!/bin/sh\n')
        handle.write('export PATH=' + shlex.quote(environment(executable)['PATH']) + '\n')
        handle.write('cd ' + shlex.quote(directory.name) + '\n')
        if provider == 'pi':
            handle.write("printf '%s\\n' 'In pi, use /login to choose a provider. Exit pi when finished.'\n")
        handle.write(shlex.join(login_command(provider, executable)) + '\n')
        handle.write('printf "%s" "$?" > ' + shlex.quote(done) + '\n')
    os.chmod(script, 0o700)
    try:
        subprocess.run(['open', '-a', 'Terminal', script], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.SubprocessError):
        directory.cleanup()
        raise DiscoveryError('Could not open Terminal for sign-in.') from None
    return directory
