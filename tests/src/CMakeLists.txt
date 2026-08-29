# SPDX-License-Identifier: LGPL-2.1-or-later
# Modified by the Cadex project, 2026. See docs/FREECAD.md.

add_subdirectory(Base)
add_subdirectory(App)
# The Gui test suite links FreeCADGui and includes Qt widget headers, so it
# only exists when the GUI is built. Every other kept workbench already
# guards its own Gui subdirectory this way (cadex ADR-022).
if(BUILD_GUI)
    add_subdirectory(Gui)
endif()
add_subdirectory(Mod)
add_subdirectory(zipios++)
