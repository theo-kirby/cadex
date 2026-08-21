# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Which parts are printable: the ticks, which are ours (cadex ADR-158).

The engine hands back a **roster** — every accepted output that *could*
become an STL — and knows nothing else about printing until an export names
the parts to write. The ticks are this file's, and they live in the scene:

- **the roster** is cached per project root, filled off the ``inspect
  scope="script"`` block the backend already adopts on open and after every
  accepted rebuild (``_adopt_script_state``). A panel's ``draw`` runs on
  every redraw and must not talk to a subprocess, so this is what makes the
  checkboxes drawable at all — the arrangement ``model.load_specs`` already
  has for the parameter specs.
- **the ticks** are one scene ID property, ``cadex_printable``. Stored on
  the scene rather than in the engine's ``script.json`` because a tick is a
  decision about a view of the model, like a selection: it belongs to the
  file you are looking at it in, it costs the engine nothing, and it saves
  and reloads with the .blend for free. Newline-joined, because an ID
  property array holds numbers and an output name may not carry a control
  character.

A tick therefore costs **no round trip at all** — no store write, no
revision, nothing to fail. Drift is handled here too: a name the accepted
revision stopped publishing is dropped when the roster is adopted, which is
the same rebuild that dropped the part (cadex ADR-039).
"""

#: The scene ID property the ticks live in. Read through the helpers below,
#: never directly: the newline join is an implementation detail of "an ID
#: property is a string" and nothing outside this file should know it.
_MARKS_KEY = "cadex_printable"

#: The last roster read from the engine, per project root, so two open
#: models do not show each other's parts.
_ROSTER = {}


def _key(scene):
    from . import cadex_backend

    return str(cadex_backend.project_root(scene) or "")


def _stored(scene):
    """The ticked names as the scene holds them, in tick order."""

    raw = scene.get(_MARKS_KEY) if scene is not None else None
    if not isinstance(raw, str):
        return []
    return [name for name in raw.split("\n") if name]


def _store(scene, names):
    ordered = []
    for name in names:
        name = str(name or "")
        if name and name not in ordered:
            ordered.append(name)
    if ordered:
        scene[_MARKS_KEY] = "\n".join(ordered)
    elif _MARKS_KEY in scene.keys():
        # Nothing ticked is the absence of the property rather than an empty
        # string in it: a .blend that never printed anything and one that
        # unticked its last part should read the same.
        del scene[_MARKS_KEY]
    return ordered


def cached(scene):
    """The roster as last read, without touching the engine. May be ``[]``."""

    return list(_ROSTER.get(_key(scene)) or ())


def adopt(scene, block):
    """Take the roster out of one ``inspect scope="script"`` block.

    The free path, and the one that matters: a rebuild is what changes which
    outputs exist, so this is also where a tick for a part the script has
    stopped publishing is dropped — anywhere later and the panel would draw
    a tick that is no longer real.
    """

    entries = list((block or {}).get("outputs") or [])
    roster = [dict(entry) for entry in entries if isinstance(entry, dict)]
    _ROSTER[_key(scene)] = roster
    names = {str(entry.get("name") or "") for entry in roster}
    stored = _stored(scene)
    if [name for name in stored if name not in names]:
        _store(scene, [name for name in stored if name in names])


def refresh(scene):
    """Re-read the roster from the engine. Returns the list, or ``[]``."""

    from . import cadex_backend

    entries = cadex_backend.script_printable(scene)
    if entries is None:
        return cached(scene)
    _ROSTER[_key(scene)] = [dict(entry) for entry in entries]
    return cached(scene)


def marked(scene):
    """The ticked names that the accepted revision still publishes.

    Filtered rather than trusted: the roster can have moved under a scene
    that has not adopted one since, and naming a part the engine no longer
    publishes would turn a whole export into one refusal.
    """

    names = {str(entry.get("name") or "") for entry in cached(scene)}
    return [name for name in _stored(scene) if name in names]


def is_marked(scene, name):
    """Whether one output is ticked. What the panel draws its icon from."""

    return str(name or "") in _stored(scene)


def toggle(scene, name):
    """Flip one output's tick. ``(ok, report)``.

    Checked against the roster rather than taken on trust: the operator
    carries a name out of a panel that may not have redrawn since the last
    rebuild, and a tick for a part that no longer exists would sit there
    looking real until the export refused it.
    """

    name = str(name or "")
    entries = cached(scene) or refresh(scene)
    if not any(str(entry.get("name") or "") == name for entry in entries):
        return False, ("{:s} is not one of this model's printable outputs. "
                       "Rebuild, then try again.".format(name))
    stored = _stored(scene)
    if name in stored:
        _store(scene, [row for row in stored if row != name])
    else:
        _store(scene, stored + [name])
    return True, ""
