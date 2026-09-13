# Wren independent-copy lifecycle

Verified against source: 2026-09-12. [Cadex-new]

For current status, see the [interruption/retry experiment](INTERRUPTION.md).
The following is the retained iteration 54 copy-switch evidence.

The working project became `ot5-wren-copy54`. The persistent private-network
port 8765 serves this copy and defaults to retained `wren2-final` (105 mm feet),
visibly HISTORICAL relative to the copy's accepted 110 mm feet and disabled
policy. Select ACCEPTED NOW to inspect the copy-only edit. No new training
attempt or product-agent authorship is claimed. Wren's D9 authorship gap remains
open; this is D7 isolation evidence.

[copy-evidence.json](copy-evidence.json) records the real lifecycle test.
With all authoring/training/rendering writers stopped, the complete Wren
project was copied, including hidden files, assets and retained run artifacts.
The persistent service was deliberately switched to the copy and its project
and current-run identity checked through headless Chromium at the private URL.
The source directory was then renamed out of its original location for the
entire edit, engine restore and browser check. A `finally` block restored it.
The original's complete file inventory stayed byte-identical.

The public CLI set `foot_len=110` and `policy_on=0` only in the copy, rendered
its accepted model and restored it through two fresh engine processes. A
second, separately started review server and the persistent operator server
both loaded all six retained run models with their own revision/digest/specs,
all three recorded metric histories, and all four videos. Videos played,
survived polling and downloaded with their recorded SHA-256 digests. The two
servers returned identical historical mesh hashes and review identities.
Accepted view showed the copy's changed identity and parameters with no old
video substituted. Return-to-current selected historical `wren2-final`.
The second server was stopped; the persistent service stays running.

Reproduce from the unchanged 105 mm Wren source and an absent destination,
with writers stopped (do not reuse an already edited destination):

```bash
cp -R "$HOME/cadex-projects/ot5-wren" "$HOME/cadex-projects/ot5-wren-copy54"
systemctl --user stop cadex-operator-review
systemd-run --user --unit=cadex-operator-review --property=Restart=on-failure \
  --working-directory="$PWD" "$PWD/cadex" review \
  --project "$HOME/cadex-projects/ot5-wren-copy54" \
  --host "$(tailscale ip -4)" --port 8765
PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  pixi run python docs/probes/wren-fresh/copy_lifecycle.py \
  "$HOME/cadex-projects/ot5-wren" "$HOME/cadex-projects/ot5-wren-copy54" \
  "http://$(tailscale ip -4):8765/"
```

The assertion-based lifecycle test refuses a changed source or incomplete
copy, checks inventory preservation including assets and every run file,
and retains CLI logs, inventory, browser screenshots and receipt in the copy's
`evidence/copy54/`. Restore receipts live in `evidence/copy54-restore/`.
A different absent sibling destination may be used; update the service and
published operator status accordingly. It never deletes prior copies.

This is a same-machine private-network browser observation, not a second-device
test. The original path was unavailable, not inaccessible by all possible
filesystem routes. Existing videos were retained, not re-rendered; no new D11
similarity evidence is claimed. Checkpoint review snapshots contain 19 points
per curve, final reviews and training runs 240; the test compares against each
retained progress file rather than assuming they share a history length.
Earlier probe drafts incorrectly expected override values for every parameter
and 240 samples for checkpoint reviews. Both assumptions were corrected;
failed draft copies remain outside the repository for audit.
