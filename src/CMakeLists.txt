# Modified by the Cadex project, 2026. See docs/FREECAD.md.
# SPDX-License-Identifier: LGPL-2.1-or-later

add_subdirectory(Build)
add_subdirectory(3rdParty)
add_subdirectory(Base)
add_subdirectory(App)
add_subdirectory(Main)
add_subdirectory(Mod)
add_subdirectory(Ext)
add_subdirectory(Doc)


if(BUILD_TEMPLATE)
    add_subdirectory(Tools/_TEMPLATE_)
endif(BUILD_TEMPLATE)

# Cadex (ADR-629): src/MacAppBundle (the macOS app bundle and QuickLook
# plugin) is no longer configured; there is no application to bundle.

