# SPDX-FileCopyrightText: 2026 Cadex Authors
# SPDX-License-Identifier: LGPL-2.1-or-later
"""What does an accepted design export under today's engine, and does it smoke?

ADR-393 fixed the exported pose of a welded body. A project accepted *before*
that fix keeps the wrong model in its pinned accepted attempt, and
``cadex smoke`` reads exactly that pin — so on `ot7-plover-e` the only model
the shipped command can measure is the defective one, and its first-frame
agreement gate refuses before any verdict exists. The design cannot be
re-accepted without a product-agent turn, and the ot7 charter forbids the
actor making one.

This probe splits the two halves the shipped command joins, so the corrected
model can be measured without writing a design:

``restore PROJECT`` opens the project with the ordinary restore pass, which
re-runs the accepted script and re-exports every artifact under today's
engine. It reports what ``open_project`` made of the result — *including its
refusal*, which is itself the measurement: a digest that moved says the engine
now exports something else. The rebuilt attempt is left on disk either way,
because that is where the freshly exported model is.

``smoke PROJECT --attempt DIR`` then runs the shipped ``cadex smoke`` with one
thing changed: the digest-checked bundle is read from the named attempt
directory rather than from the accepted pin. Everything after that — the
MuJoCo rollout, the exact-solid geometry check and its first-frame agreement
against the published clearance — is the product's own code, unmodified, and
the receipt it writes is an ordinary ``cadex-smoke-v1``.

Neither half writes a script, a parameter or an accepted state, and both
should be pointed at a copy regardless: a restore that refuses rolls the
accepted state back, but it still leaves a new attempt and a moved
``latest_candidate`` behind.

    pixi run python docs/probes/ot7/runner/reexport_smoke.py restore PROJECT
    pixi run python docs/probes/ot7/runner/reexport_smoke.py smoke PROJECT \\
        --attempt PROJECT/script_artifacts/<revision>/attempt-<id> --out DIR
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / 'cli'))


def state_snapshot(project: Path) -> dict:
    """The identity fields a restore may move, plus the attempts on disk."""

    state = json.loads((project / 'script.json').read_text())
    return {
        'accepted_revision': state.get('accepted_revision'),
        'accepted_digest': state.get('accepted_digest'),
        'accepted_attempt': state.get('accepted_attempt'),
        'accepted_geometry': state.get('accepted_geometry'),
        'working_revision': state.get('working_revision'),
        'latest_candidate': state.get('latest_candidate'),
        'attempts': sorted(
            str(path.relative_to(project))
            for path in project.glob('script_artifacts/*/attempt-*')
        ),
    }


def restore(project: Path) -> dict:
    """Re-run the accepted script through today's engine and report the open.

    A refusal is a result rather than an error here, so the reply is returned
    whole instead of raised: ``CADEXD_RESTORE_FAILED`` carries the accepted
    and restored digests, and on the ADR-389 path the geometry digests too.
    """

    from cadex_cli.client import CadexdClient
    from cadex_cli.engine import resolve_engine
    from cadex_cli.session import project_lock

    project = Path(project).resolve()
    row = {'project': project.name, 'before': state_snapshot(project)}
    engine = resolve_engine(None)
    row['engine'] = engine.describe()
    client = CadexdClient(engine)
    started = time.monotonic()
    with project_lock(project, wait=True):
        try:
            client.start()
            reply = client.request(
                'open_project', {'project_root': str(project), 'restore': True}
            )
        finally:
            client.shutdown()
    row['seconds'] = round(time.monotonic() - started, 3)
    row['open'] = {
        key: reply.get(key)
        for key in ('ok', 'error', 'failure_code', 'restore', 'observed')
        if key in reply
    }
    row['after'] = state_snapshot(project)
    row['accepted_pin_preserved'] = (
        row['before']['accepted_attempt'] == row['after']['accepted_attempt']
        and row['before']['accepted_digest'] == row['after']['accepted_digest']
    )
    row['rebuilt_attempts'] = [
        name for name in row['after']['attempts'] if name not in row['before']['attempts']
    ]
    return row


def compare_attempts(first: Path, second: Path) -> dict:
    """Which outputs of two attempts of the same revision differ, and how.

    Named separately from the digests because "the digest moved" is not a
    finding — *which* of ninety outputs moved it is. An output is compared on
    its canonical definition, its solved placement and its artifact bytes,
    which between them are what the project digest is built from.
    """

    def outputs(attempt: Path) -> dict:
        result = json.loads((attempt / 'result.json').read_text())
        return {item['name']: item for item in result['outputs']}, result

    left, left_result = outputs(Path(first))
    right, right_result = outputs(Path(second))
    changed = []
    for name in sorted(set(left) | set(right)):
        before, after = left.get(name), right.get(name)
        if before is None or after is None:
            changed.append({'output': name, 'missing_from': 'first' if before is None else 'second'})
            continue
        reasons = {}
        if json.dumps(before.get('definition'), sort_keys=True) != json.dumps(
                after.get('definition'), sort_keys=True):
            reasons['definition'] = True
        if before.get('solved_placement_matrix') != after.get('solved_placement_matrix'):
            reasons['placement'] = True
        for side, attempt in ((before, Path(first)), (after, Path(second))):
            path = side.get('artifact_path')
            side['_bytes'] = (
                hashlib.sha256((attempt / path).read_bytes()).hexdigest() if path else ''
            )
        if before['_bytes'] != after['_bytes']:
            reasons['artifact'] = {
                'kind': before.get('artifact_kind'),
                'first_sha256': before['_bytes'],
                'second_sha256': after['_bytes'],
            }
        if reasons:
            changed.append({'output': name, **reasons})
    return {
        'first': str(first), 'second': str(second),
        'outputs': len(left), 'changed': changed,
        'digests': [left_result.get('digest'), right_result.get('digest')],
    }


def bundle_from(staging: Path):
    """``cadex smoke``'s retained bundle, read from a named attempt.

    The same containment and digest checks the shipped reader makes — an
    artifact must live inside the attempt directory and hash to what the
    attempt's own ``result.json`` says — minus the one check that cannot hold
    here: that the result's digest equals the project's accepted digest. It
    does not, and that is the whole reason this exists.
    """

    from cadex_cli.smoke import SmokeError

    staging = Path(staging).resolve()

    def read(root: Path, destination: Path):
        state = json.loads((Path(root) / 'script.json').read_text())
        result = json.loads((staging / 'result.json').read_text())
        if not result.get('ok'):
            raise SmokeError(f'{staging.name} did not build; there is nothing to smoke')
        destination = Path(destination).resolve()
        if destination == Path(root).resolve() or destination.is_relative_to(staging):
            raise SmokeError('--out must not overwrite the project or the attempt')
        destination.mkdir(parents=True, exist_ok=True)
        for name in ('smoke.json', 'smoke-dynamics.json', 'smoke-trace.json', 'smoke-geometry.json'):
            (destination / name).unlink(missing_ok=True)
        items = {item['name']: item for item in result['outputs']}
        display = {}
        for name, item in items.items():
            if not item.get('artifact_path'):
                continue
            source = (staging / item['artifact_path']).resolve()
            if not source.is_relative_to(staging) or not source.is_file():
                raise SmokeError(f'missing or escaping retained artifact: {name}')
            if item.get('artifact_sha256') and hashlib.sha256(
                    source.read_bytes()).hexdigest() != item['artifact_sha256']:
                raise SmokeError(f'retained artifact digest mismatch: {name}')
            target = destination / source.name
            target.unlink(missing_ok=True)
            shutil.copyfile(source, target)
            display[name] = {'artifact_kind': item.get('artifact_kind'),
                             'artifact_path': str(target)}
        return state, items, display

    return read


def smoke(project: Path, staging: Path, out: Path, seconds: float = 1.0,
          timeout: float = 240.0) -> dict:
    """``cadex smoke`` on the named attempt's model, through the shipped path."""

    from cadex_cli import __main__ as cli
    from cadex_cli.report import RunReport
    from cadex_cli.smoke import SmokeError

    project, staging, out = Path(project).resolve(), Path(staging).resolve(), Path(out).resolve()
    args = cli.build_parser().parse_args(
        ['smoke', '--project', str(project), '--out', str(out),
         '--seconds', f'{float(seconds):g}', '--timeout', f'{float(timeout):g}', '--json'])
    report = RunReport()
    shipped, cli.retained_bundle = cli.retained_bundle, bundle_from(staging)
    started = time.monotonic()
    try:
        code = cli.command_smoke(args, report)
    except SmokeError as exc:
        # `main` turns this into an envelope; a model whose bodies are in the
        # wrong place fails the geometry check's first-frame agreement gate
        # and raises here, which is the control this probe exists to show.
        report.error, code = str(exc), cli.EXIT_FAILURE
    finally:
        cli.retained_bundle = shipped
    return {'project': project.name, 'attempt': staging.name, 'exit_code': code,
            'seconds': round(time.monotonic() - started, 3),
            'error': report.error, 'accepted_revision': report.accepted_revision,
            'smoke': report.smoke}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    one = sub.add_parser('restore', help='re-run the accepted script through today engine')
    one.add_argument('project', type=Path)
    two = sub.add_parser('smoke', help='smoke a named attempt of the accepted revision')
    two.add_argument('project', type=Path)
    two.add_argument('--attempt', type=Path, required=True)
    two.add_argument('--out', type=Path, required=True)
    two.add_argument('--seconds', type=float, default=1.0)
    two.add_argument('--timeout', type=float, default=240.0)
    three = sub.add_parser('compare', help='which outputs differ between two attempts')
    three.add_argument('first', type=Path)
    three.add_argument('second', type=Path)
    args = parser.parse_args(argv)
    if args.command == 'restore':
        row = restore(args.project)
        print(json.dumps(row, indent=2))
        return 0 if row['open'].get('ok') else 1
    if args.command == 'compare':
        print(json.dumps(compare_attempts(args.first, args.second), indent=2))
        return 0
    row = smoke(args.project, args.attempt, args.out, args.seconds, args.timeout)
    print(json.dumps(row, indent=2, default=str))
    return int(row['exit_code'])


if __name__ == '__main__':
    raise SystemExit(main())
