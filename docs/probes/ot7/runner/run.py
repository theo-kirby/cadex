# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bounded, project-local evidence collection for the frozen ot7 attempts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
from pathlib import Path
import re
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[4]
PROMPTS = REPO / 'docs/probes/ot7/prompts'
sys.path.insert(0, str(REPO / 'cli'))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def digest(path):
    return {'path': path.name, 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def frozen(design):
    names = [f'{design}.create.prompt.txt'] + [f'continue-{i}.prompt.txt' for i in range(1, 4)]
    table = dict(re.findall(r'\| `([^`]+\.prompt\.txt)` \| .*? \| \d+ \| `([a-f0-9]{64})`',
                            (PROMPTS / 'README.md').read_text()))
    for name in names:
        if digest(PROMPTS / name)['sha256'] != table[name]:
            raise ValueError(f'frozen prompt changed: {name}')
    return names


def child_turn(project, out, prompt, model):
    from cadex_cli import __main__ as cli
    from cadex_cli.agent import ClaudeTurn, TurnResult, find_claude

    original = cli.command_prompt

    class CapturedTurn(ClaudeTurn):
        def __init__(self, **kwargs):
            kwargs['claude_path'] = find_claude('')
            super().__init__(**kwargs)
            self.invoked = False

        def run(self, text):
            if self.invoked:
                write(out / 'blocked-followup.json', {'reason': 'Only the frozen prompt is authorized.'})
                return TurnResult(error='unfrozen automatic follow-up blocked')
            self.invoked = True
            result = super().run(text)
            with (out / 'transcript.jsonl').open('w') as stream:
                for frame in result.frames:
                    stream.write(json.dumps(frame) + '\n')
            return result

    cli.command_prompt = lambda args, report: original(args, report, turn_factory=CapturedTurn)
    args = ['--project', str(project), '--json', '--model', model,
            '--out', str(out / 'exports'), '-p', prompt.read_text()]
    if prompt.name.startswith('continue-'):
        args.append('--resume')
    try:
        return cli.main(args)
    finally:
        cli.command_prompt = original


def child_measure(project, out):
    from cadex_cli import __main__ as cli
    from cadex_cli.clearance import fit_summary
    from cadex_cli.inventory import _read_path
    from cadex_cli.report import RunReport
    args = cli.build_parser().parse_args(['clearance', '--project', str(project)])
    with cli._engine_session(args, RunReport(), restore=False) as (_, client):
        value = _read_path(client, {'scope': 'clearance', 'target': ''}, '')
        write(out / 'clearance.json', value)
        write(out / 'fit.json', fit_summary(value))
        write(out / 'inventory.json', _read_path(client, {'scope': 'inventory', 'target': ''}, ''))
    return 0


def execute(command, out, stem, timeout):
    start = time.monotonic()
    with (out / f'{stem}.stdout.json').open('w') as stdout, (out / f'{stem}.stderr.txt').open('w') as stderr:
        try:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            code = 'timeout'
        except OSError as exc:
            stderr.write(str(exc))
            code = 'launch_failed'
    return {'exit_code': code, 'elapsed_seconds': time.monotonic() - start}


def run(design, project, model, execute_call=execute):
    names = frozen(design)
    project = project.resolve()
    if project.is_relative_to(REPO) or project.parent.name != 'cadex-projects' or not project.name.startswith('ot7-'):
        raise ValueError('Use a new ot7-* project in the external cadex-projects directory.')
    # Exclusive creation is also the restart/duplicate-dispatch guard. No seed edits.
    project.mkdir()
    evidence = project / 'evidence'
    evidence.mkdir()
    receipt = {'schema': 'ot7-design-evidence-v1', 'design': design, 'project': project.name,
               'model': model, 'actor_design_edits': 0, 'turns': [], 'status': 'running'}
    save = lambda: write(evidence / 'attempt.json', receipt)
    save()
    for index, name in enumerate(names):
        out = evidence / f'turn-{index}'
        out.mkdir()
        prompt = out / name
        prompt.write_bytes((PROMPTS / name).read_bytes())
        row = {'index': index, 'continuations_used': index, 'prompt': digest(prompt), 'status': 'started'}
        receipt['turns'].append(row)
        save()  # Persist the consumed slot before launching the provider.
        row['turn'] = execute_call([sys.executable, str(Path(__file__).resolve()), '--child-turn',
                                   str(project), str(out), str(prompt), model], out, 'turn', 1800)
        row['measurement'] = execute_call([sys.executable, str(Path(__file__).resolve()), '--child-measure',
                                          str(project), str(out)], out, 'measurement', 300)
        if (out / 'fit.json').exists():
            fit = json.loads((out / 'fit.json').read_text())
            row['static_fit'] = {key: fit[key] for key in ('verdict', 'failing_count', 'pairs_checked')}
        row['status'] = 'completed'
        row['artifacts'] = [digest(p) for p in sorted(out.iterdir()) if p.is_file()]
        save()
        # Provider failures and ambiguous interrupted turns stop this attempt.
        if row['turn']['exit_code'] not in (0, 3) or (out / 'blocked-followup.json').exists():
            receipt['status'] = 'interrupted'
            break
    else:
        receipt['status'] = 'exhausted'
    # One bounded smoke, even on a failing fit; it never modifies the design.
    smoke = evidence / 'smoke'
    smoke.mkdir()
    receipt['smoke'] = execute_call([str(REPO / 'cadex'), 'smoke', '--project', str(project),
                                    '--out', str(smoke), '--seconds', '1', '--timeout', '240', '--json'],
                                   smoke, 'smoke', 300)
    receipt['smoke']['artifacts'] = [digest(p) for p in sorted(smoke.iterdir()) if p.is_file()]
    save()
    return receipt


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child-turn':
        sys.exit(child_turn(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]))
    if len(sys.argv) > 1 and sys.argv[1] == '--child-measure':
        sys.exit(child_measure(Path(sys.argv[2]), Path(sys.argv[3])))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('design', choices=['heron', 'robin', 'plover'])
    parser.add_argument('project', type=Path)
    parser.add_argument('--model', default='claude-fable-5')
    args = parser.parse_args()
    print(json.dumps(run(args.design, args.project, args.model), indent=2))
