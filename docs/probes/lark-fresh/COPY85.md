# Lark independent-copy lifecycle (D7)

Verified against source: 2026-09-13. [Cadex-new] Iteration 85, ADR-314.

The working project became **`ot5-lark-copy85`**. The persistent
private-network port 8765 was deliberately switched to this copy and stays
on it, defaulting to the retained `lark2-final` (80 mm feet, the product
agent's 45 mm torso), visibly HISTORICAL relative to the copy's accepted
90 mm feet and disabled policy. Select ACCEPTED NOW to inspect the copy-only
edit. No new training attempt and no product-agent authorship is claimed;
this is D7 isolation evidence on the third fresh project, with Lark's D9
lifecycle already complete ([REVISION84.md](REVISION84.md)).

[`copy85-evidence.json`](copy85-evidence.json) is the compact receipt of
the real lifecycle test, guarded by `cli/tests/test_lark_fresh_evidence.py`.
With no authoring, training or rendering writer active, the complete
`ot5-lark` project (1,852 files, hidden files, assets and every retained run
artifact included) was copied with the destination absent, and a SHA-256
inventory of the original was taken before the copy. The persistent service
was stopped and started on the copy, then checked over the private address:
project `ot5-lark-copy85`, accepted revision `ca88f223b54c…`, six runs. The
original directory was then renamed out of its location for the entire
edit, engine restore and browser pass; a `finally` block put it back, and
its inventory matched the pre-copy snapshot byte for byte (1,852 files),
checked once by the driver and once independently afterwards.

The public CLI set `foot_len=90` and `policy_on=0` only in the copy
(accepted revision `083d086ad980…`, digest `4c4171abfa4f…`, differing from
the original's `ca88f223b54c…` / `a1232a4a8c26…`), rendered its accepted
model and restored it through two fresh engine processes (PIDs 3821742 and
3821789, `matches_accepted: true`, retained accepted-attempt bytes
unchanged). A second, separately started review server and the persistent
operator server both loaded all six retained run models with their own
revision, digest and 80 mm `foot_len`, all six recorded metric histories
(240 points per curve for the training runs and final reviews, 19 for the
checkpoint reviews), and all four videos, which played, survived a poll and
downloaded with their recorded SHA-256 digests. The two servers returned
identical mesh hashes and review identities for every run; the accepted
view showed the copy's changed identity and parameters with no video
substituted, and return-to-current selected historical `lark2-final`. The
250 retained `runs/` and `assets/` files in the copy are byte-identical to
the original's. The second server was stopped; the persistent service keeps
serving the copy, and a fresh visit after the original was restored is
recorded as `evidence/lark2-final-switch85-browser.json` in the copy.

Reproduce from the unchanged 80 mm Lark source and an absent destination,
with writers stopped (do not reuse an already edited destination):

```bash
cp -R "$HOME/cadex-projects/ot5-lark" "$HOME/cadex-projects/ot5-lark-copy85"
systemctl --user stop cadex-operator-review
systemd-run --user --unit=cadex-operator-review --property=Restart=on-failure \
  --working-directory="$PWD" "$PWD/cadex" review \
  --project "$HOME/cadex-projects/ot5-lark-copy85" \
  --host "$(tailscale ip -4)" --port 8765
PYTHONPATH=cli:cli/tests OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  pixi run python docs/probes/lark-fresh/copy_lifecycle.py \
  "$HOME/cadex-projects/ot5-lark" "$HOME/cadex-projects/ot5-lark-copy85" \
  "http://$(tailscale ip -4):8765/" copy85 lark2-final foot_len=80:90 policy_on=1:0
PYTHONPATH=cli:cli/tests pixi run python docs/probes/wren-fresh/current.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-lark-copy85" lark2-final switch85
```

`copy_lifecycle.py` is the Wren copy driver with nothing named after a
project: the run a fresh visit must select and the parameter changes are
arguments, the component count comes from each run's served model, and the
curve lengths from each retained progress file. It refuses a changed source
or an incomplete copy, retains CLI logs, the inventory, both browser
screenshots and the receipt in the copy's `evidence/copy85/`, and the
restore receipts in `evidence/copy85-restore/`. It never deletes prior
copies.

Limits: a same-machine private-network browser observation, not a
second-device test. The original path was unavailable, not inaccessible by
every filesystem route. Existing videos were retained, not re-rendered; no
new D11 similarity evidence is claimed. Changing the copy through the CLI
here means a parameter edit; retraining on the copy is not claimed.
