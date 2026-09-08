---
node_id: 9daeb01e-2be7-5214-8dbe-e7cab6b343da
slug: tiny-haven-0347
title: Payload resolution checks schema agreement, not worker completeness
created_at: '2026-09-08T01:27:16+00:00'
parents:
- spring-wolf-7431
summary: ''
---
## What

Qualified the CLI payload resolver's schema-check boundary with two disposable synthetic payloads. A nonempty manifest/module schema mismatch was refused; equal schemas resolved with worker and API modules absent. No runtime behavior, tests, real bundle or project artifacts changed.

## Why

Execute short-plan rank 1 from [rec: spring-wolf-7431], serving missions 1, 2 and 6 and protecting the working charter criteria **The walk exists and is tested headlessly** (crisp-reef-5607) and **The agent can see its work without a screen** (damp-moon-9297). The public payload-coherence guarantee needs an accurately bounded interpretation. This experiment supplies the evidence for the selected subtractive guidance correction, not a new lifecycle qualification or a runtime defect claim.

The injected overseer request for a maintainer/planner pass is already reflected in the current checkpoint and subsequent bet. The dispatch's explicit prohibition on reconcile controls this contributor iteration; assume the persisted short plan is authoritative. Existing bundled-engine success remains complete, with no refresh, GUI startup or portability claim. No Later criterion is promoted.

## Method

Read STATE.md, the graph contract, actor and record skills, the causal bet, VISION, cli/cadex_cli/engine.py and protocol.py, and cli/tests/test_engine_resolution.py. The fixture follows that suite's minimal payload shape but uses an exit-97 stub; resolution never executes it.

Run from the repository root with `pixi run python -` and this stdin (temporary directories are automatically removed):

```python
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
sys.path.insert(0, str(Path('cli').resolve()))
from cadex_cli.engine import EngineError, resolve_engine
from cadex_cli.protocol import load_protocol
source = Path('src/Mod/cadex').resolve()
actual = load_protocol(source).PROTOCOL_SCHEMA
with TemporaryDirectory(prefix='cadex-schema-probe-') as scratch:
    for case, declared in [('mismatch', actual + '-mismatch'), ('match-missing-worker', actual)]:
        root = Path(scratch) / case
        binary = root / 'bin/FreeCADCmd'
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/bin/sh\nexit 97\n')
        binary.chmod(0o755)
        modules = root / 'Mod/cadex'
        modules.mkdir(parents=True)
        shutil.copy2(source / 'CadexdProtocol.py', modules)
        (root / 'cadex-engine.json').write_text(json.dumps(dict(schema='cadex-engine-v1', protocol=declared, freecadcmd='bin/FreeCADCmd', module_dir='Mod/cadex')))
        assert sorted(p.name for p in modules.iterdir()) == ['CadexdProtocol.py']
        assert not (modules / 'CadexWorker.py').exists()
        assert not (modules / 'CadexAssemblyAPI.py').exists()
        try:
            engine = resolve_engine(root)
        except EngineError as exc:
            assert case == 'mismatch'
            assert 'declares protocol' in str(exc)
            print(f'{case}: REFUSED; ' + str(exc).replace(str(root), '<fixture>'))
        else:
            assert case == 'match-missing-worker'
            assert engine.protocol.PROTOCOL_SCHEMA == actual
            print(f'{case}: RESOLVED; schema={actual}; source={engine.source}; worker/API absent')
print('PASS: resolver-only probe; no process spawned; disposable fixtures removed')
```

Run existing resolution tests: `pixi run python -m pytest cli/tests/test_engine_resolution.py -q`. No new committed tests, full CLI suite, build, training, worker execution or packaged gate: this unit changes only its evidence record and qualifies resolution alone.

## Result

Probe exit 0. Output (temporary path normalized):

```text
mismatch: REFUSED; <fixture>/cadex-engine.json declares protocol 'cadex-cadexd-v1-mismatch' but its CadexdProtocol says 'cadex-cadexd-v1'.
match-missing-worker: RESOLVED; schema=cadex-cadexd-v1; source=explicit; worker/API absent
PASS: resolver-only probe; no process spawned; disposable fixtures removed
```

Existing engine-resolution gate exit 0: **10 passed in 0.47s**, zero skips. The resolver checks named paths and loads CadexdProtocol; nonempty schema disagreement is rejected. Matching schema strings do not establish complete worker imports or coherent source provenance. This does not reproduce or explain the earlier bundle's particular missing import, and does not qualify worker execution.

Next: short-plan rank 2 is now supported: remove the docs/CLI.md section 6 payload-coherence overclaim and, if needed, its matching engine.py comment, with the selected doc/scaffold checks and zone gates. The lifecycle and headless-review criteria remain working on their prior evidence; nothing additional is missing from those accepted headless criteria on account of this resolver probe. The guidance correction remains unlanded; GUI attachment and remote execution remain documented/scripted only. No ROADMAP checkbox or removal ADR is needed for this evidence-only experiment. The state checkpoint has one pending record before this unit; reconciliation remains the separate maintainer's responsibility.

Dispatch closed: 1 unit — confirmed the resolver's schema-only boundary with disposable fixtures and 10 passing existing tests.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: 17b28946cf199ba5539317cd9216aa41d3e21dac

## State Impact

- target: chilly-union-8972 — synthetic resolver probe refuses nonempty schema mismatch but accepts matching schemas with worker/API modules absent; 10 existing resolution tests pass; guidance correction remains next
