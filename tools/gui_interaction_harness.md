# FreeCAD GUI Interaction Harness

`tools/gui_interaction_harness.py` launches a FreeCAD GUI binary with an
isolated user profile, optionally under `xvfb-run`, and runs
`tools/gui_interaction_driver.py` inside FreeCAD.

The driver enumerates registered workbenches, switches through them, records
menus, toolbars, actions, and Qt widgets, and exercises common controls:
buttons, menu actions, combo boxes, line edits, spin boxes, sliders, tabs, and
item views. It writes `summary.json` and `events.jsonl`.

Example:

```sh
tools/gui_interaction_harness.py build/release --output-dir /tmp/freecad-gui-report
```

Useful bounded smoke run:

```sh
tools/gui_interaction_harness.py build/release \
  --output-dir /tmp/freecad-gui-smoke \
  --max-workbenches 2 \
  --max-interactions 50 \
  --max-targets 800
```

Survey without activating widgets:

```sh
tools/gui_interaction_harness.py build/release --mode survey
```

By default, the harness skips actions with labels that commonly open files,
write data, quit the application, alter preferences, launch help, or manage
addons/macros. Use `--allow-risky` only with a disposable environment when you
want those clicks included.

This is an exhaustive enumerator over the Qt objects exposed during the run,
not a mathematical proof that every possible user path in FreeCAD has been
covered. Workbenches and dialogs often create controls lazily after a command
is run, a document is selected, or a task panel enters a specific state. The
JSONL report is intended to make those coverage gaps visible so focused runs
can add fixtures and state setup for specific workbenches.
