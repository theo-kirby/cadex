---
node_id: 9fa55bb3-eb05-5a2e-9538-775871a6f9cf
slug: silver-rain-7333
title: Output-loss consent and cold recovery qualified through the CLI
created_at: '2026-09-08T08:27:58+00:00'
parents:
- rich-creek-7708
summary: ''
---
## What

Qualified output-loss consent and cold recovery through six fresh ordinary CLI processes against one external disposable project and the existing staged engine. The contract holds: refusal preserves the accepted two-output model; explicit replacement accepts the single-output model; both reopen headlessly. No product code changed.

## Why

Executes short unit 1 selected by [rec: rich-creek-7708], serving missions 1 and 2 and preserving charter criteria **File lifecycle** and **The walk exists and is tested headlessly**. This is standing maintenance of completed lifecycle evidence, not another walk or a newly closed criterion. The work-iteration prohibition on reconciliation overrides the embedded overseer instruction to run a separate maintainer; the supplied checkpoint already contains the Git correction and the planner selected this bounded qualification. No reconciliation or replanning files are edited here.

Existing recovery tests separately cover dropped_outputs, replace=True, failed candidate rollback and accepted-source restoration, but the inspected CLI commands and packaged lifecycle tests do not establish this complete cross-process transition. Therefore use the one fresh-project experiment permitted by the bet. No provider, training, GUI, remote dispatch, stage refresh, concurrency campaign or durable project mutation. No Later criterion promotion.

## Method

At product HEAD a2e4e24375fcdebef80ae3e5167b02b5b2b4a5ee, read STATE.md, the Hypergraph contract/record skill, the Ouroboros actor skill, VISION, docs/CLI.md script flags and reporting contract, cli/cadex_cli/__main__.py command_script, report.py, cli/tests/test_commands.py and engine test_project_store_recovery.py. Inspect dropped_outputs and its PROJECT_OUTPUTS_DROPPED call path in CadexScriptedRuntime.py. Use build/engine/cadex-engine-0.0.0-macos-arm64 unchanged.

Create an external temporary directory holding project P, two.py and one.py. Exact sources:

```python
# two.py
result = {"frame": part.box(10, 10, 2), "cap": part.box(4, 4, 1)}
# one.py
result = {"frame": part.box(10, 10, 2)}
```

Seed P/DECISIONS.md with an explicit keep-two-until-consent decision and P/docs/sensors.md with a no-sensors fixture note. Let ordinary CLI acceptance initialize Git and scaffold missing ARCHITECTURE.md and PROGRESS.md. Store a 113-byte ASCII one-triangle spare.stl through the ordinary asset command (no policy/checkpoint/trace). For each invocation below add `--engine "$E" --project "$P" --json`; each is its own subprocess with a 120-second timeout:

1. `./cadex script --set "$T/two.py"`
2. `./cadex asset --put "$T/spare.stl"`
3. `./cadex script --set "$T/one.py"`
4. `./cadex script`
5. `./cadex script --set "$T/one.py" --replace`
6. `./cadex script`

Save stdout, stderr, script.json and script.py after every boundary in the external cadex-i194 temporary directory. Assert exact accepted revision/digest/contracts across refusal and cold restore, the final one-output acceptance and cold restore, and protected bytes for DECISIONS.md, ARCHITECTURE.md, docs/sensors.md and assets/spare.stl after every transition. PROGRESS.md legitimately appends accepted-run rows; it is not required to remain byte-identical. No manual store metadata edits or repair operations. Run `pixi run python -m pytest src/Mod/cadex/cadex_tests/test_project_store_recovery.py -q`. Raw temporary evidence is not committed; commands, sources and substantive results are reproduced here without machine paths.

## Result

All six actual CLI exits were **0, 0, 3, 0, 0, 0**, respectively. Every snapshot assertion passed. Existing focused recovery suite: **14 passed in 0.43s**, no skips.

Use A = revision `93402a9a1dc30ee629e552baf3913b846a1f7d333e025eac7b9ae1c5c2524b87`, digest `fafb0cf9d4a05067631fdd6920914c3593c16bd5192c552477d9e29164e90791`; B = revision `6d56e34729e6b80bf2679990ca54886e84ce3eae3deecd4202f683a4ac586e2b`, digest `336fd4c12895560879bb072f5536227ef02ac20a9919892b0745f041f5ab7ba2`.

- Initial acceptance and subsequent asset storage: working=accepted=A, accepted contract frame/cap, both part solids. CLI initializes the project repository and commits ordinary accepted work. Stored spare.stl sha256 is `1f81bebab1f10ec1a5777130c99c478fc0a727149e4db4f6ffabcf008e002707`.
- Refusal: exit 3, latest_candidate status failed at B with failure_code **PROJECT_OUTPUTS_DROPPED** and the message naming cap and requiring replace=true for intentional removal. Working and accepted remain A, accepted digest and frame/cap contract unchanged. The working source is the original two-output source. The refusal's JSON envelope reports revision A but blank accepted_revision/digest and outputs []; the error string carries the refusal reason, while the structured failure_code is in script.json.latest_candidate. This is the current reporting limitation, not evidence that accepted geometry vanished. Commands without --out also have empty exported outputs arrays on success; accepted names here come from the stored contract.
- Cold read: exit 0; stdout equals two.py exactly, including when --json is requested (documented print-script behavior). Working=accepted=A, same digest and two accepted outputs. Restore refreshes accepted_attempt/latest_candidate to a successful attempt. No explicit recovery submission was needed.
- Explicit replacement: exit 0, working=accepted=B with B digest; accepted contract is frame only. Source equals one.py. Successful JSON includes B identity and ordinary commit note.
- Final cold read: exit 0; stdout equals one.py exactly; working/accepted revision, digest and frame-only contract remain B.

Protected docs and stored asset bytes stayed identical through all four transition calls. PROGRESS.md contains only the initial script acceptance, asset storage and explicit replacement rows, with A/B numbers; refusal and cold reads add no rows. This verifies preservation of this fixture, not every possible asset type or failure class.

No consent/recovery mismatch was demonstrated, so conditional short unit 2 is **not dispatchable** on this evidence. Return to planning; do not repeat this experiment, broaden the rejection survey or infer a new reporting feature from blank failure-envelope fields. The existing lifecycle charter completion evidence stands; no missing lifecycle leg was identified and no additional criterion can be ticked by this unit. No behavior/doc/scaffold changes, removal ADR or ROADMAP feature checkbox apply. No full build, full CLI/engine suite or packaged lifecycle suite is claimed: this experiment changed only the record, used six real staged CLI invocations and passed the relevant existing recovery tests. Hypergraph export/check is the recording gate. The unreconciled tail will be two records, including this one; a separate maintainer owns it.

Dispatch closed: 1 unit — output-loss refusal, explicit consent and cold recovery qualified; no corrective product unit warranted.

## Repo

- repo: git@github.com:theo-kirby/cadex.git
- branch: ouroboros/nt3
- commit: a2e4e24375fcdebef80ae3e5167b02b5b2b4a5ee

## State Impact

- target: simple-willow-8989 — Real staged CLI output-loss refusal preserved accepted outputs and protected docs/assets; cold restore and explicit replacement both succeed
- target: chilly-union-8972 — Six-process consent transition qualified; rejection exits 3 with PROJECT_OUTPUTS_DROPPED in store, failure envelope accepted identity remains blank; no consent/recovery correction warranted
- target: calm-peak-5247 — Standing file-lifecycle qualification preserves completed walk evidence; no missing leg identified and conditional correction is not dispatchable
