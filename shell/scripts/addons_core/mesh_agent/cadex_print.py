# SPDX-FileCopyrightText: 2026 Mesh Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Which parts are printable: the panel's side of it (cadex ADR-156).

The engine holds the marks — a list of accepted output names — and hands
back a roster: every output that *could* become an STL, with a flag saying
whether it is ticked. ``set_printable`` replaces that list **wholesale**,
so a checkbox is a read, a flip and a push of the whole list, and this
module is where those three lines live rather than in ``ui.py``.

The cache is what makes the panel drawable at all. A panel's ``draw`` runs
on every redraw and must not talk to a subprocess, so the roster is drawn
from memory — the arrangement ``model.load_specs`` already has for the
parameter specs.

Filling it costs **nothing**: the roster rides in the ``inspect
scope="script"`` block the backend already adopts on open and after every
accepted rebuild (``_adopt_script_state``), so there is no extra round trip
and no moment where the panel is showing a roster older than the model.
"""

#: The last roster read from the engine, per project root, so two open
#: models do not show each other's parts.
_ROSTER = {}


def _key(scene):
    from . import cadex_backend

    return str(cadex_backend.project_root(scene) or "")


def cached(scene):
    """The roster as last read, without touching the engine. May be ``[]``."""

    return list(_ROSTER.get(_key(scene)) or ())


def adopt(scene, block):
    """Take the roster out of one ``inspect scope="script"`` block.

    The free path, and the one that matters: a rebuild is what changes which
    outputs exist, and the engine drops the mark of an output the script
    stopped publishing — so a roster adopted anywhere later than here would
    draw a tick that is no longer real.
    """

    entries = list((block or {}).get("outputs") or [])
    _ROSTER[_key(scene)] = [dict(entry) for entry in entries
                            if isinstance(entry, dict)]


def invalidate(scene=None):
    """Forget the cache; the next ``refresh`` re-reads it."""

    if scene is None:
        _ROSTER.clear()
        return
    _ROSTER.pop(_key(scene), None)


def refresh(scene):
    """Re-read the roster from the engine. Returns the list, or ``[]``."""

    from . import cadex_backend

    entries = cadex_backend.script_printable(scene)
    if entries is None:
        return cached(scene)
    _ROSTER[_key(scene)] = [dict(entry) for entry in entries]
    return list(_ROSTER[_key(scene)])


def marked(scene):
    """The ticked names, in roster order."""

    return [str(entry.get("name") or "") for entry in cached(scene)
            if entry.get("printable")]


def toggle(scene, name):
    """Flip one output's mark and push the whole list. ``(ok, report)``.

    Reads the roster first rather than trusting the cache the panel drew:
    the roster can have moved under a panel that has not redrawn since the
    last rebuild, and pushing a stale list would silently un-tick a part.
    """

    from . import cadex_backend

    name = str(name or "")
    entries = refresh(scene)
    if not any(str(entry.get("name") or "") == name for entry in entries):
        return False, ("{:s} is not one of this model's printable outputs. "
                       "Rebuild, then try again.".format(name))
    wanted = []
    for entry in entries:
        entry_name = str(entry.get("name") or "")
        ticked = bool(entry.get("printable"))
        if entry_name == name:
            ticked = not ticked
        if ticked:
            wanted.append(entry_name)
    payload = cadex_backend.set_printable(scene, wanted)
    if payload.get("ok") is not True:
        invalidate(scene)
        return False, str(payload.get("error") or payload)
    _ROSTER[_key(scene)] = [dict(entry) for entry in
                            list(payload.get("outputs") or [])
                            if isinstance(entry, dict)]
    return True, ""
