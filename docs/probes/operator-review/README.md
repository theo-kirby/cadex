# Persistent Reed operator review

Verified against source: 2026-09-12. [Cadex-new]

The shared private-network dashboard on port 8765 now serves
`ot5-biped-copy29`, the independent Reed working copy. Its latest recorded
attempt is `copy100`, completed at revision `25d9b6ab7472…` with 100 mm feet.
Nine retained runs include the original 70 mm design and the 90 mm revision.
The subsequent product-agent revision requests were refused before authorship;
they did not create another walk attempt. No training is active at this check.

Keep the server running between iterations. On this Linux host, from the
checkout, the detached command is:

```bash
systemd-run --user --unit=cadex-operator-review --property=Restart=on-failure \
  --working-directory="$PWD" "$PWD/cadex" review \
  --project "$HOME/cadex-projects/ot5-biped-copy29" \
  --host "$(tailscale ip -4)" --port 8765
```

For a deliberate working-project switch, stop `cadex-operator-review` with
`systemctl --user stop cadex-operator-review`, start the command with the new
project, and verify the same URL. This transient user service survives actor
exit and tests; it is not a reboot installation. Do not restart Ouroboros or
training. Update this published status on experiment start/completion and
project switches.

The read-only probe uses the existing persistent server; it never launches or
stops a test server:

```bash
PYTHONPATH=cli:cli/tests pixi run python docs/probes/operator-review/verify.py \
  "http://$(tailscale ip -4):8765/" "$HOME/cadex-projects/ot5-biped-copy29" copy100
```

The committed `evidence.json` records the observed project/run/model identity,
real saved-video playback and matching download digest, preserved playback on
poll, historical `probe3-final` selection and return to current. This was a
headless Chromium observation through this machine's private-network address,
not a second-device test or an observation during new GPU training. D10 still
needs the persistent URL observed across a real experiment start/completion.
