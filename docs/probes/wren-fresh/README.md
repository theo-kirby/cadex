# Fresh Wren reopen and persistent review

Verified against source: 2026-09-12. [Cadex-new]

The corrected iteration 46 probe passes on `ot5-wren`, accepted revision
`5309bebc6597…`, digest `dbd02d7c12a0…`. The persistent private-network
port 8765 now serves Wren and stays running. A same-machine headless Chromium
visit loaded in 0.84 s, drew eight components (seven biped solids plus ground), showed twelve parameter defaults,
orbited and zoomed through real pointer input, and kept ACCEPTED NOW with zero
runs after polling. This is no second-device or training/video claim.

[evidence.json](evidence.json) is the compact receipt. Screenshots remain in
`ot5-wren/evidence/lifecycle46/`, with hashes in the receipt. Two engine
processes restored accepted identity on a disposable full copy. The served
project's 66 files were unchanged, excluding only this invocation's evidence
directory and `.git`. Earlier evidence directories are included. Both Reed
inventories matched (582 and 1017 files). Those snapshots were taken during
iteration 46 before the successful probe, after the server switch; they do
not establish isolation during Wren's earlier creation.

Run from the checkout, with pre-recorded SHA-256 inventories for Reed:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/lifecycle.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-wren" lifecycle46 \
  --intact "$HOME/cadex-projects/ot5-biped=/tmp/ot5-biped-iteration46.json" \
  --intact "$HOME/cadex-projects/ot5-biped-copy29=/tmp/ot5-biped-copy29-iteration46.json"
```

The previous iteration committed the probe and receipt tests without a receipt
or record. Its product-agent creation reached an accepted script but the CLI
exited 1 on a provider session limit; project decision completion and training
are not claimed. This unit supplies the missing causal handoff.

The requested evidence-directory exclusion exposed additional faulty probe
assumptions: the endpoint is `/api/project`, and empty parameter overrides mean
values are shown in the declared-default column. Engine restore also rewrites
attempt metadata and replaces artifacts, dropping retained tessellation. Early
failed runs exercised that on Wren. An explicit public `rebuild` with standard
display regenerated the view; accepted revision and digest were asserted
unchanged. Copy-based reopens now avoid modifying served inputs. Thus this
receipt proves copy reopen plus read-only browser preservation, **not in-place
restore preservation**; the lost-tessellation behavior remains a demonstrated
D6 concern for the next unit. No product code or dependency changed.

The screenshot was inspected: the eight solids include Wren's modeled ground
plate, so the predecessor test's expected count of seven was wrong. This is
not a new D11 similarity assessment. The inventory regression also changes
an earlier evidence file and verifies it is still detected; generating this
invocation's screenshot alone does not change the inventory.
