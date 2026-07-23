# SPDX-License-Identifier: LGPL-2.1-or-later

# VibeCAD keeps only the headless CSG-to-OCC conversion core from the former
# OpenSCAD workbench. The user-facing source workflow lives in PartDesign.
SET(OpenSCADConversion_SRCS
    Init.py
    InitGui.py
    OpenSCAD2Dgeom.py
    OpenSCADFeatures.py
    OpenSCADUtils.py
    exportCSG.py
    importCSG.py
    tokrules.py
)
SOURCE_GROUP("" FILES ${OpenSCADConversion_SRCS})

ADD_CUSTOM_TARGET(OpenSCADConversion ALL
    SOURCES ${OpenSCADConversion_SRCS}
)

fc_copy_sources(
    OpenSCADConversion
    "${CMAKE_BINARY_DIR}/Mod/OpenSCAD"
    ${OpenSCADConversion_SRCS}
)

INSTALL(
    FILES ${OpenSCADConversion_SRCS}
    DESTINATION Mod/OpenSCAD
)
