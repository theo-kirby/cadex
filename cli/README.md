# `cli/` — Cadex as a headless CLI

`LGPL-2.1-or-later`, like the rest of the repository
(`docs/PROVENANCE.md` §7). The Blender shell it replaced was
`GPL-2.0-or-later` and is deleted (ADR-498); **no file here may be copied
from it**, including from the `v1-blender-shell` tag. Its protocol client,
backend, MCP shim and modes were reference and nothing more. Every
equivalent in this package derives from the LGPL engine-side precedents —
`cadex_tests/cadexd_latency_integration.py` and
`cadex_tests/test_cadexd_lifecycle.py` — and the prompt text is written
fresh. See ADR-061.

Full documentation: [`../docs/CLI.md`](../docs/CLI.md).

```bash
./cadex mcp --project ./b          # register with your agent's MCP client
./cadex guidance                   # the text that server gives the agent
./cadex params --project ./b --set bore=8 --out ./b/v2
./cadex app                        # the read-only dashboard (docs/DASHBOARD.md)
pixi run python -m pytest cli/tests
```

Run it from the repository root through the `./cadex` shim; it needs a built
engine (`pixi run build-engine`) or `--engine <staged payload>`.
