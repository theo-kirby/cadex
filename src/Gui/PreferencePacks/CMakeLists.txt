SET(PreferencePacks_Files
        "package.xml"
)

SET(PreferencePacks_Directories
        "FreeCAD Classic"
        "Dark behave"
        "FreeCAD Light"
        "FreeCAD Dark"
        "CadexDark"
        "CadexLight"
        "CadexMono"
        "Cadex Preferences"
)

SET(PreferencePacks_Config_Files
        "FreeCAD Classic/FreeCAD Classic.cfg"
        "Dark behave/Dark behave.cfg"
        "FreeCAD Light/FreeCAD Light.cfg"
        "FreeCAD Dark/FreeCAD Dark.cfg"
        "CadexDark/CadexDark.cfg"
        "CadexLight/CadexLight.cfg"
        "CadexMono/CadexMono.cfg"
        "Cadex Preferences/Cadex Preferences.cfg"
)

ADD_CUSTOM_TARGET(PreferencePacks_data ALL
        SOURCES ${PreferencePacks_Files} ${PreferencePacks_Config_Files}
)

fc_copy_sources(PreferencePacks_data "${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_DATADIR}/Gui/PreferencePacks"
        ${PreferencePacks_Files}
        ${PreferencePacks_Config_Files})

INSTALL(
        FILES
        ${PreferencePacks_Files}
        DESTINATION
        ${CMAKE_INSTALL_DATADIR}/Gui/PreferencePacks
)

INSTALL(
        DIRECTORY
        ${PreferencePacks_Directories}
        DESTINATION
        ${CMAKE_INSTALL_DATADIR}/Gui/PreferencePacks
)
