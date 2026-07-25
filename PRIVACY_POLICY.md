# Cadex Privacy Policy

Last updated: 2026-07-25. Cadex is pre-release software under active
development. This policy describes what the code in this repository does
today, and every claim below names the file you can check it against.

Cadex is an AI-native CAD application. Part of using it is sending what you
write, and what you are modeling, to an AI provider. This document exists to
be specific about which part.

## Summary

- **Cadex itself collects nothing.** No telemetry, no analytics, no crash
  reporting, no account, no phone-home.
- **The assistant is not local.** When you send a chat message, Cadex runs
  the Claude Code CLI on your machine, which transmits your message — and
  the results of the tools it calls, including viewport screenshots — to
  Anthropic, under *your own* Claude Code login.
- **Your conversation is stored inside your `.blend` file.** Sharing the
  file shares the transcript.

## 1. What Cadex collects about you

Nothing. There is no telemetry, usage reporting, analytics, licence check,
update check, or crash reporter anywhere in the code we wrote. Cadex has no
accounts and no servers; the project operates no infrastructure that could
receive your data.

This is checkable rather than asserted: no file under `src/Mod/cadex/` or
`shell/scripts/addons_core/mesh_agent/` opens an outbound network
connection. The only sockets either half creates are loopback — the add-on's
tool bridge binds `127.0.0.1` on an ephemeral port (`mesh_agent/bridge.py`)
and the MCP shim connects back to it on `127.0.0.1`
(`mesh_agent/mcp_shim.py`). The engine (`cadexd`) speaks NDJSON over
stdin/stdout to a process on the same machine and opens no socket at all.

## 2. What leaves your machine when you use the assistant

Cadex does not talk to any AI provider itself. It holds no API keys, no
base URLs, and no model client. Each chat turn instead spawns the **Claude
Code CLI** (`claude -p`) as a subprocess on your machine
(`mesh_agent/backend.py`). Claude Code owns the model loop and the network
connection, authenticated with the Claude Code login you already have.

**Cadex never sees, stores, or transmits your credentials.** If you have not
installed and signed in to Claude Code, the assistant does not run.

What Claude Code sends to Anthropic during a turn:

- Your chat message, and the system prompt describing the CAD tools.
- The conversation so far — resumed across turns by session id.
- **The result of every tool the assistant calls.** The tool surface is
  defined in `mesh_agent/tools.py`; those that carry your data are:

  | Tool | What it sends |
  |---|---|
  | `get_script`, `write_script`, `edit_script` | the project script — the full source of your model |
  | `set_params`, `inspect_model` | parameter values, geometry measurements, feature and subshape names |
  | `describe_cad_api` | nothing of yours (static API documentation) |
  | `scene_summary` | the names and structure of the objects in your scene |
  | `viewport_screenshot` | **an image of your 3D viewport** |
  | `get_attached_image` | any reference image you attach to a message |
  | `export_stl` | mesh geometry, written out for the assistant to read back |

  Screenshots and attached images are the two worth pausing on: whatever is
  visible in the viewport, or in a file you attach, goes to Anthropic.

Once that data reaches Anthropic it is governed by **Anthropic's** privacy
policy and the terms of your Claude Code plan, not by this one — including
any question of whether it is retained or used for training. Cadex is not a
party to that relationship. See
<https://www.anthropic.com/legal/privacy>.

Dragging a parameter slider does **not** involve the AI. Sliders re-run the
script through the local engine directly, and nothing leaves your machine.

## 3. What is stored on your machine

- **Your `.blend` file contains the conversation.** The chat transcript and
  the Claude Code session id are saved into the file as a text datablock
  named `mesh_chat.json` (`mesh_agent/history.py`). This is deliberate — the
  conversation belongs to the design — but it means **sending someone a
  `.blend` sends them everything you and the assistant said in it.** Clear
  the chat before sharing a file if that matters to you.
- **The project store** sits beside the `.blend` in a `<stem>.cadex/`
  directory: the project script and its revisions. Local only.
- **A per-session temporary directory** (`mesh_agent_*` under your system
  temp) holds the MCP config naming the loopback port and the bridge's
  single-session token. No personal data, and no reason to outlive the
  session.
- **Claude Code keeps its own session history** on your machine, under its
  own directory and its own policy. The session id saved in the `.blend` is
  a pointer into that store; the stored transcript itself is Claude Code's.
- **Inherited local storage.** Both halves keep configuration, logs, caches,
  thumbnails, and recent-file lists in your user directories, as FreeCAD and
  Blender always have. This may contain private data such as file paths. It
  stays on local storage.

## 4. Inherited components that can reach the network

Cadex is built from forks of FreeCAD and Blender (see
[`docs/PROVENANCE.md`](docs/PROVENANCE.md)), and some inherited features
have network behavior of their own:

- **FreeCAD's Addon Manager, which fetches add-ons from the internet, is not
  shipped.** The engine payload installs only the modules on an explicit
  keep-list (`package/engine/build_engine_payload.sh`); the Addon Manager,
  Web, and Start modules are not on it. Neither is FreeCAD's online User
  Manual, which is part of the GUI that this product does not build.
- **Blender's online features remain in the shell** — the extensions system
  and its remote repositories. These are governed by Blender's own "Allow
  Online Access" preference, a user-controlled opt-in, and by the Blender
  Foundation's policies. Cadex does not use them and does not enable them
  for you.
- **Blender does not auto-run scripts embedded in `.blend` files** in this
  build: `WITH_PYTHON_SECURITY` is `ON` (`shell/CMakeLists.txt`), which
  disables that by default. See [`SECURITY.md`](SECURITY.md) for why that
  matters when you open a file from someone else.
- **Loading or saving to a remote server** — over any protocol your platform
  supports — shares your IP and whatever else that protocol's normal
  connection flow involves. That is between you and the remote host.

## 5. Files you export

CAD files carry metadata. A STEP, STL, or `.blend` you export may contain
local directory paths, and a path can reveal your username — as in
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

*This is Cadex's privacy policy only. It is not FreeCAD's or Blender's, and
Cadex is endorsed by neither project. Its structure is descended from the
FreeCAD privacy policy, which was in turn based on the
[GIMP privacy policy](https://www.gimp.org/about/privacy.html).*
