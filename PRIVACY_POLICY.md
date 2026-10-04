# Cadex Privacy Policy

Last updated: 2026-10-04. Cadex is pre-release software under active
development. This policy describes what the code in this repository does
today, and every claim below names the file you can check it against.

Cadex is an AI-native CAD application: an engine, a dashboard, and the tools
an AI agent of your choice uses to drive them. Part of using it is your
agent sending what you write, and what you are modeling, to an AI provider.
This document exists to be specific about which part.

## Summary

- **Cadex itself collects nothing.** No telemetry, no analytics, no crash
  reporting, no account, no phone-home.
- **The assistant is not local, and it is yours.** Cadex runs no AI. The
  agent you connect to `cadex mcp` — Claude Code, Codex, or another —
  transmits your prompts and the results of the Cadex tools it calls,
  including rendered images of your model, to its own provider, under your
  own login with that agent.
- **Your project directory records how the design was made.** Sharing the
  directory shares that record.

## 1. What Cadex collects about you

Nothing. There is no telemetry, usage reporting, analytics, licence check,
update check, or crash reporter anywhere in the code we wrote. Cadex has no
accounts and no servers; the project operates no infrastructure that could
receive your data.

This is checkable rather than asserted: no file under `src/Mod/cadex/` or
`cli/cadex_cli/` opens an outbound network connection. The sockets Cadex
creates are local:

- `cadex mcp` speaks to the agent that started it over its own
  stdin/stdout and opens no socket (`cli/cadex_cli/mcp.py`);
- the dashboard, `./cadex app`, listens on `127.0.0.1` unless you give
  it another `--host`, and only serves reads (`cli/cadex_cli/review_server.py`,
  `cli/cadex_cli/__main__.py`);
- the engine (`cadexd`) speaks NDJSON over stdin/stdout to a process on the
  same machine and opens no socket at all.

The one tool that moves data to another machine is one you run by hand:
`training/remote_train.sh` copies a project to the GPU machine you name, over
your own ssh configuration (`training/SETUP.md`).

## 2. What leaves your machine when you use the assistant

Cadex does not talk to any AI provider itself. It holds no API keys, no
base URLs, and no model client, and it starts no agent (ADR-538). You run an
agent — Claude Code, Codex, or another MCP client — and that agent starts
`cadex mcp` as a subprocess on your machine. The agent owns the model loop
and the network connection, authenticated with your own login with it.

**Cadex never sees, stores, or transmits your credentials.**

What your agent sends to its provider while it works a Cadex project
(which provider, and under which terms, is that agent's business):

- Your prompts, and the guidance Cadex gives it (the server's short
  instructions, and the whole text `./cadex guidance` prints; `cli/cadex_cli/guidance.py`).
- The conversation so far, kept by your agent.
- **The result of every Cadex tool it calls.** The tool surface is
  defined in `cli/cadex_cli/tools.py`; those that carry your data are:

  | Tool | What it sends |
  |---|---|
  | `write_script`, `edit_script` | the project script — the full source of your model |
  | `set_params`, `rebuild`, `inspect` | parameter values, geometry measurements, and feature, part and subshape names |
  | `describe_api` | nothing of yours (static API documentation) |
  | `link_part`, `put_asset` | the name and contents of the part or file you point it at |
  | `look`, `draw_blueprint` | **rendered images of your model**, and a dimensioned drawing sheet of it |
  | `train_start`, `train_status`, `train_stop`, `evaluate` | training progress and evaluation results, including rendered frames of a rollout |

  Rendered images are the ones worth pausing on: whatever your model looks
  like goes to your agent's provider.

Rendered images in particular go to whichever provider your agent uses.
Once that data reaches the provider it is governed by **that provider's**
privacy policy and the terms of your plan with it, not by this one —
including any question of whether it is retained or used for training.
Cadex is not a party to that relationship. For Claude Code, see
<https://www.anthropic.com/legal/privacy>.

Changing a parameter with `./cadex params` does **not** involve the AI. It re-runs the script through the local engine
directly, and nothing leaves your machine.

## 3. What is stored on your machine

- **The project directory** is the truth of a design: the project script
  and its revisions, the project's `ARCHITECTURE.md`, `DECISIONS.md` and
  `PROGRESS.md`, renders, exports and run reports. It also holds
  `agent.json`, the project's engine budgets (`cli/cadex_cli/session.py`). Local only — but **sending someone a project
  sends them the record of how it was designed**, including the decisions
  the assistant wrote down.
- **Your agent keeps its own session history**, under its own directory
  and its own policy. Cadex keeps no transcript.
- **Inherited local storage.** The engine keeps configuration, logs and
  caches in your user directories, as FreeCAD always has. This may contain
  private data such as file paths. It stays on local storage.

## 4. Inherited components that can reach the network

Cadex's engine is built from a fork of FreeCAD (see
[`docs/PROVENANCE.md`](docs/PROVENANCE.md)), and some inherited features
have network behavior of their own:

- **FreeCAD's Addon Manager, which fetches add-ons from the internet, is not
  shipped.** The engine payload installs only the modules on an explicit
  keep-list (`package/engine/build_engine_payload.sh`); the Addon Manager,
  Web, and Start modules are not on it. Neither is FreeCAD's online User
  Manual, which is part of the GUI that this product does not build.
- **Loading or saving to a remote server** — over any protocol your platform
  supports — shares your IP and whatever else that protocol's normal
  connection flow involves. That is between you and the remote host.

## 5. Files you export

CAD files carry metadata. A STEP or STL you export may contain local
directory paths, and a path can reveal your username — as in
`C:\Users\yourname\Documents\part.step`. It is worth checking exported
metadata before sending a file to anyone. Similarly, the project script
inside a project is a readable record of how the part was designed,
comments included.

## 6. Third-party builds

Cadex is free software and may be packaged or modified by other people, who
may add software or change the source. We cannot vouch for such builds or
tell you what they do with your data. This policy describes the code in this
repository.

## 7. Changes to this policy

Cadex is pre-release and this policy will change as the product does. It is
version-controlled: `git log PRIVACY_POLICY.md` shows exactly what changed
and when. A change that means more of your data leaves your machine will
also be recorded in `docs/DECISIONS.md`.

## 8. Contact

Privacy questions and corrections: open an issue at
<https://github.com/theo-kirby/cadex/issues>. If a privacy problem is also a
security problem, report it privately — see [`SECURITY.md`](SECURITY.md).

---

*This is Cadex's privacy policy only. It is not FreeCAD's, and Cadex is not
endorsed by the FreeCAD project. Its structure is descended from the
FreeCAD privacy policy, which was in turn based on the
[GIMP privacy policy](https://www.gimp.org/about/privacy.html).*
