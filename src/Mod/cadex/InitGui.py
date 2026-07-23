# SPDX-License-Identifier: LGPL-2.1-or-later

"""GUI bootstrap for the shared Cadex assistant."""

from __future__ import annotations

import FreeCAD as App


def _warn(message: str) -> None:
    App.Console.PrintWarning(f"{message}\n")


def _restore_cadex_disabled_workbenches() -> bool:
    """Undo only the exact disabled lists previously written by Cadex."""

    preferences = App.ParamGet(
        "User parameter:BaseApp/Preferences/Workbenches"
    )
    disabled = frozenset(
        item.strip()
        for item in preferences.GetString("Disabled", "").split(",")
        if item.strip()
    )
    disabled_sets_to_repair = (
        frozenset(
            {
                "InspectionWorkbench",
                "MaterialWorkbench",
                "OpenSCADWorkbench",
                "PointsWorkbench",
                "ReverseEngineeringWorkbench",
                "RobotWorkbench",
                "TestWorkbench",
                "NoneWorkbench",
            }
        ),
        frozenset(
            {
                "InspectionWorkbench",
                "MaterialWorkbench",
                "PointsWorkbench",
                "ReverseEngineeringWorkbench",
                "RobotWorkbench",
                "TestWorkbench",
                "NoneWorkbench",
            }
        ),
    )
    if disabled not in disabled_sets_to_repair:
        return False
    preferences.SetString("Disabled", "TestWorkbench,NoneWorkbench")
    return True


try:
    _restore_cadex_disabled_workbenches()
except Exception as exc:
    _warn(f"Cadex workbench preference migration failed: {exc}")


try:
    from PySide import QtCore

    import CadexGui

    CadexGui.ensure_commands_registered()

    def _open_startup_assistant() -> None:
        try:
            import CadexGui as _CadexGui

            _CadexGui.ensure_commands_registered()
            _CadexGui.show_assistant_for_active_workbench()
        except Exception as exc:
            try:
                import FreeCAD as _App

                _App.Console.PrintWarning(
                    f"Cadex assistant startup open failed: {exc}\n"
                )
            except Exception:
                pass

    def _apply_experimental_mode() -> None:
        try:
            import CadexExperimentalMode

            CadexExperimentalMode.activate()
        except Exception as exc:
            try:
                import FreeCAD as _App

                _App.Console.PrintWarning(
                    f"Cadex experimental mode startup failed: {exc}\n"
                )
            except Exception:
                pass

    def _setup_always_on_grid() -> None:
        try:
            import CadexGrid

            CadexGrid.setup()
        except Exception as exc:
            try:
                import FreeCAD as _App

                _App.Console.PrintWarning(f"Cadex grid startup setup failed: {exc}\n")
            except Exception:
                pass

    QtCore.QTimer.singleShot(0, _open_startup_assistant)
    QtCore.QTimer.singleShot(0, _apply_experimental_mode)
    QtCore.QTimer.singleShot(0, _setup_always_on_grid)
except Exception as exc:
    _warn(f"Cadex GUI bootstrap failed: {exc}")
