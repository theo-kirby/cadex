# `cli/` — Cadex as a headless CLI

`LGPL-2.1-or-later`, the engine side of the repository
(`docs/PROVENANCE.md` §1). **No file here may be copied from `shell/`**,
which is `GPL-2.0-or-later`; the shell's `cadexd_client.py`, `backend.py`,
`mcp_shim.py` and `modes.py` are reference and nothing more. Every
equivalent in this package derives from the LGPL engine-side precedents —
`cadex_tests/cadexd_latency_integration.py` and
`cadex_tests/test_cadexd_lifecycle.py` — and the prompt text is written
fresh. See ADR-061.

Full documentation: [`../docs/CLI.md`](../docs/CLI.md).

```bash
./cadex -p "a 40x25x15 mm bracket with a 6 mm bore" --project ./b --out ./b/out
./cadex params --project ./b --set bore=8 --out ./b/v2
./cadex -p "add a 2 mm fillet to the vertical edges" --project ./b --resume
pixi run python -m pytest cli/tests
```

Run it from the repository root through the `./cadex` shim; it needs a built
engine (`pixi run build-engine`) or `--engine <staged payload>`.
