# SPDX-FileCopyrightText: 2026 Cadex Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""The registry of presentation views, and the three hooks they share.

Five modules restyle the viewport without touching the script — collision
(ADR-091), dimensions (ADR-139), section (ADR-148), explode (ADR-149),
blueprint (ADR-150) — and before this module each of them was hand-wired
into the same call sites: :func:`cadex_backend.hydrate` after every accepted
response, :func:`cadex_backend._finish_preview` after every applied preview,
and :func:`capture.render_views` around the "what did I build" render. Five
copies of the same wiring is how the sixth one gets wired wrong, so the
wiring is now data: a view registers a record, and the call sites walk the
registry.

A record carries up to three hooks, each optional:

- ``on_hydrate(payload, root, animate)`` — called on every accepted
  response, in ``order``. Returns the view's report dict (written into the
  hydration under the view's name) or None to write nothing. An exception
  costs the view and never the geometry: it is caught per record and
  reported as ``{"shown": False, "error": ...}``, exactly as the hand-wired
  blocks did.
- ``on_preview(scene)`` — called after a preview's poses are applied
  (``apply_placements`` just overwrote ``matrix_world``), in ``order``.
  No report; an exception is printed and the next view still runs.
- ``suspend()`` — returns an undo callable, or None if there was nothing to
  suspend. ``render_views`` calls these in ``order`` before it measures the
  model (bounds are evaluated, so a view left on would be framed), and the
  one undo :func:`suspend_for_render` returns unwinds them in reverse.

``order`` is the contract the hand wiring kept implicitly and the registry
keeps explicitly: collision 20, section 30, explode 40, dimensions 50,
blueprint 60. Section before explode is load-bearing on the preview path
(the clip planes are re-aimed before the explosion re-poses); dimensions
last because it reads the shapes every earlier view has finished posing.
"""

import traceback


class _View:
    __slots__ = ("name", "order", "on_hydrate", "on_preview", "suspend")

    def __init__(self, name, order, on_hydrate, on_preview, suspend):
        self.name = name
        self.order = order
        self.on_hydrate = on_hydrate
        self.on_preview = on_preview
        self.suspend = suspend


_registry = {}


def register_view(*, name, order, on_hydrate=None, on_preview=None,
                  suspend=None):
    """Add (or replace) a view record. Keyword-only, so a call site reads."""

    _registry[str(name)] = _View(str(name), int(order),
                                 on_hydrate, on_preview, suspend)


def unregister_view(name):
    _registry.pop(str(name), None)


def registered():
    """The view records, in ``order``."""

    return sorted(_registry.values(), key=lambda view: (view.order, view.name))


def hydrate_views(hydration, payload, root, animate):
    """Run every view's hydrate hook over one accepted response.

    Per-record try/except: a malformed record costs its own view and never
    the geometry, and never the views after it — the terms every hand-wired
    block already stated for itself.
    """

    for view in registered():
        if view.on_hydrate is None:
            continue
        try:
            report = view.on_hydrate(payload, root, animate)
        except Exception:
            hydration[view.name] = {"shown": False,
                                    "error": traceback.format_exc()}
            traceback.print_exc()
        else:
            if report is not None:
                hydration[view.name] = report
    return hydration


def preview_views(scene):
    """Run every view's preview hook after a preview's poses landed."""

    for view in registered():
        if view.on_preview is None:
            continue
        try:
            view.on_preview(scene)
        except Exception:
            traceback.print_exc()


def suspend_for_render():
    """Suspend every view that knows how; returns the one undo.

    Suspends in ``order`` — before the caller measures the model, because
    bounds are evaluated and a view left on would be framed — and the undo
    unwinds in reverse order, which is the nesting the hand-wired
    ``finally`` block kept.
    """

    undos = []
    for view in registered():
        if view.suspend is None:
            continue
        undo = view.suspend()
        if undo is not None:
            undos.append(undo)

    def restore():
        for undo in reversed(undos):
            undo()

    return restore


# -- the two views with no register() of their own ---------------------------

def _collision_hydrate(payload, root, animate):
    """The collision overlay (ADR-091), on the geometry's own terms.

    Mid-drag (``animate=False``) it CLEARS rather than lags. The shapes it
    draws are attached to a model that is being re-solved every debounce
    tick, and a wire cage left over from the previous shape is worse than
    no wire cage — this whole feature exists because collision geometry in
    the wrong place is invisible. Same trade the simulation bake makes.
    """

    from . import cadex_collision

    if animate:
        return cadex_collision.apply(payload, root)
    if cadex_collision.enabled():
        cadex_collision.clear()
        return {"shown": False, "reason": "mid-drag"}
    return None


def _dimensions_hydrate(payload, _root, _animate):
    """The dimension overlay (ADR-139): refresh on EVERY response.

    Mid-drag included, and it does not clear the way collision does: a
    dimension is measured on the shape in front of you and re-published
    with it, so mid-drag the numbers are current rather than lagging. The
    opposite trade from a wire cage, for the opposite reason — a cage left
    over from the previous shape is wrong, and a number recomputed for
    this one is right.
    """

    from . import cadex_dimension

    return cadex_dimension.apply(payload)


def install():
    """Register the views that own no ``register()`` of their own.

    Collision and dimensions register no PropertyGroup and no class, so
    they have nowhere to self-register from; the modules that do
    (section, explode, blueprint) call :func:`register_view` inside their
    own ``register()``.
    """

    register_view(name="collision", order=20, on_hydrate=_collision_hydrate)
    register_view(name="dimensions", order=50, on_hydrate=_dimensions_hydrate)


def uninstall():
    _registry.clear()
