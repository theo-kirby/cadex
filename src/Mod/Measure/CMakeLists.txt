# Modified by the Cadex project, 2026. See docs/FREECAD.md.
# SPDX-License-Identifier: LGPL-2.1-or-later

add_subdirectory(App)

set(Measure_Scripts
    Init.py
    MassProperties.py
    MassPropertiesGui.py
    UtilsMeasure.py
    MeasureCOM.py
)


add_custom_target(MeasureScripts ALL
    SOURCES ${Measure_Scripts}
)

fc_target_copy_resource(MeasureScripts
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_BINARY_DIR}/Mod/Measure
    ${Measure_Scripts})

INSTALL(
    FILES
    ${Measure_Scripts}
    DESTINATION
        Mod/Measure
)
