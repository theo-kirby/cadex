# SPDX-License-Identifier: LGPL-2.1-or-later
# /**************************************************************************
#                                                                           *
#    Copyright (c) 2023 Ondsel <development@ondsel.com>                     *
#                                                                           *
#    This file is part of FreeCAD.                                          *
#                                                                           *
#    FreeCAD is free software: you can redistribute it and/or modify it     *
#    under the terms of the GNU Lesser General Public License as            *
#    published by the Free Software Foundation, either version 2.1 of the   *
#    License, or (at your option) any later version.                        *
#                                                                           *
#    FreeCAD is distributed in the hope that it will be useful, but         *
#    WITHOUT ANY WARRANTY; without even the implied warranty of             *
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU       *
#    Lesser General Public License for more details.                        *
#                                                                           *
#    You should have received a copy of the GNU Lesser General Public       *
#    License along with FreeCAD. If not, see                                *
#    <https://www.gnu.org/licenses/>.                                       *
#                                                                           *
# **************************************************************************/
# Modified by the Cadex project, 2026. See docs/FREECAD.md.

import FreeCAD

translate = FreeCAD.Qt.translate


def preferences():
    return FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/Assembly")


class PreferencesPage:
    def __init__(self, parent=None):
        # Imported here, not at module scope: preferences() is a plain
        # ParamGet that the App-level solver needs (JointObject.solveIfAllowed),
        # while PreferencesPage is the only GUI user in this module. A
        # headless build has no FreeCADGui (cadex ADR-022), and a
        # module-scope import made the whole module unimportable there --
        # which silently turned Preferences into None in JointObject's
        # ImportError guard and broke every joint.
        import FreeCADGui

        self.form = FreeCADGui.PySideUic.loadUi(":preferences/Assembly.ui")

    def saveSettings(self):
        pref = preferences()
        pref.SetBool("LeaveEditWithEscape", self.form.checkBoxEnableEscape.isChecked())
        pref.SetBool("LogSolverDebug", self.form.checkBoxSolverDebug.isChecked())
        pref.SetInt("GroundFirstPart", self.form.groundFirstPart.currentIndex())

    def loadSettings(self):
        pref = preferences()
        self.form.checkBoxEnableEscape.setChecked(pref.GetBool("LeaveEditWithEscape", True))
        self.form.checkBoxSolverDebug.setChecked(pref.GetBool("LogSolverDebug", False))
        self.form.groundFirstPart.clear()
        self.form.groundFirstPart.addItem(translate("Assembly", "Ask"))
        self.form.groundFirstPart.addItem(translate("Assembly", "Always"))
        self.form.groundFirstPart.addItem(translate("Assembly", "Never"))
        self.form.groundFirstPart.setCurrentIndex(pref.GetInt("GroundFirstPart", 0))
