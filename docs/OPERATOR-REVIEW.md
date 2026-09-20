# Follow the current run in the operator dashboard

Verified against source: 2026-09-19. [Cadex-new]

The persistent operator URL runs `tools/operator_review.py` (ADR-387).
It reads the run name from `.ouroboros/config.yml` and selects the most recent
explicitly dispatched product turn from `<projects>/<run>-*/evidence/attempt.json`.
The receipt's `project` must match its directory, so diagnostic copies cannot
steal the dashboard. Dispatch timestamps, not file modification times or a stale
`running` flag, determine the selection. A new run with no eligible dispatch
shows a waiting page; it never silently falls back to the previous run.

The existing read-only review server supplies geometry, documents, videos and
training telemetry. A small status strip shows the Ouroboros run, iteration,
state and selected project. Open tabs check every three seconds and reload when
the project or run changes. Ordinary review polling updates the selected project
between turns. A current project without accepted geometry correctly has no model
yet; a failed turn remains visible until another project is dispatched.

This is operator infrastructure, not a change to `cadex review --project`.
Future experiment drivers must publish the same receipt fields (`project`,
`turns[].window.dispatched`, and timezone-qualified `turns[].window.read_at`)
in the same layout to participate. The selection follows dispatched work, not
arbitrary actor filesystem activity. `/operator-status` returns the current
selection and the timestamp of the loop's last status update.

Run with the repository's pixi Python:

```sh
pixi run python tools/operator_review.py --repo . --projects ../cadex-projects \
  --host <tailnet-address> --port 8765
```

Install this command as the persistent `cadex-operator-review.service` user unit
with `Restart=always`, a working directory at the checkout, and enable it for
`default.target`. Use absolute deployment paths in the local unit, not in git.
The operator deployment now uses that persistent unit rather than a transient
unit pinned to a project. After installing/updating the unit, run
`systemctl --user daemon-reload` and restart it. Refresh a browser tab once when
upgrading from the old server; subsequent project switches reload automatically.

Verification: `pixi run python tools/operator_review_selftest.py` exercises real
HTTP responses and selection across project/run transitions, copied receipts,
and partial writes. The live deployment's `/operator-status` and `/api/project`
were also checked over its Tailscale-bound address.
