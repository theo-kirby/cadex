
SET(Stylesheets_Files
    "FreeCAD.qss"
    "defaults.qss"
    "VibeDark.qss"
    "VibeLight.qss"
    "VibeMono.qss"
)

SET(Parameters_Files
    "parameters/FreeCAD Dark.yaml"
    "parameters/FreeCAD Light.yaml"
)

SET(Overlay_Stylesheets_Files
    "overlay/Freecad Overlay.qss"
    "overlay/VibeDark_Overlay.qss"
    "overlay/VibeLight_Overlay.qss"
    "overlay/VibeMono_Overlay.qss"
)

# Find all the image files
FILE(GLOB Images_Files RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/images_dark-light/*.svg"
    "${CMAKE_CURRENT_SOURCE_DIR}/images_dark-light/*.png"
)

SOURCE_GROUP("Images_dark-light" FILES ${Images_Files})

FILE(GLOB Images_Files2 RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/images_classic/*.svg"
    "${CMAKE_CURRENT_SOURCE_DIR}/images_classic/*.png"
)

SOURCE_GROUP("images_classic" FILES ${Images_Files2})

FILE(GLOB Overlay_icons RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/overlay/icons/*.svg"
)

FILE(GLOB Overlay_Files RELATIVE "${CMAKE_CURRENT_SOURCE_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/overlay/*.svg"
    "${CMAKE_CURRENT_SOURCE_DIR}/overlay/*.png"
)

SOURCE_GROUP("overlay_icons" FILES ${Overlay_icons})
SOURCE_GROUP("overlay" FILES ${Overlay_Files})


ADD_CUSTOM_TARGET(Stylesheets_data ALL
    SOURCES ${Stylesheets_Files} ${Parameters_Files} ${Images_Files} ${Images_Files2} ${Overlay_Stylesheets_Files} ${Overlay_icons} ${Overlay_Files}
)

fc_copy_sources(Stylesheets_data "${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_DATADIR}/Gui/Stylesheets"
                                  ${Stylesheets_Files}
                                  ${Parameters_Files}
                                  ${Images_Files}
                                  ${Images_Files2}
                                  ${Overlay_Stylesheets_Files}
                                  ${Overlay_icons}
                                  ${Overlay_Files})

INSTALL(
    FILES
        ${Stylesheets_Files}
    DESTINATION
        ${CMAKE_INSTALL_DATADIR}/Gui/Stylesheets
)
INSTALL(
        FILES
        ${Parameters_Files}
        DESTINATION
        ${CMAKE_INSTALL_DATADIR}/Gui/Stylesheets/parameters
)
INSTALL(
    FILES
        ${Overlay_Stylesheets_Files}
        ${Overlay_Files}
    DESTINATION
        ${CMAKE_INSTALL_DATADIR}/Gui/Stylesheets/overlay
)
INSTALL(
    FILES
        ${Overlay_icons}
    DESTINATION
        ${CMAKE_INSTALL_DATADIR}/Gui/Stylesheets/overlay/icons
)
INSTALL(
    FILES
         ${Images_Files}
    DESTINATION
        ${CMAKE_INSTALL_DATADIR}/Gui/Stylesheets/images_dark-light
)
INSTALL(
    FILES
         ${Images_Files2}
    DESTINATION
        ${CMAKE_INSTALL_DATADIR}/Gui/Stylesheets/images_classic
)
