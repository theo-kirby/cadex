# Modified by the Cadex project, 2026. See docs/FREECAD.md.
# SPDX-License-Identifier: LGPL-2.1-or-later

configure_file(freecadCmd.rc.cmake ${CMAKE_CURRENT_BINARY_DIR}/freecadCmd.rc)
file(COPY cadex.ico DESTINATION ${CMAKE_CURRENT_BINARY_DIR})

if(WIN32)
    set(CADEX_LAUNCHER_DESCRIPTION "Cadex command-line portable launcher")
    set(CADEX_LAUNCHER_FILENAME "FreeCADCmd.exe")
    configure_file(
        cadexPortableLauncher.rc.cmake
        ${CMAKE_CURRENT_BINARY_DIR}/cadexCmdPortableLauncher.rc
    )
endif()

######################## FreeCADMainCmd ########################

SET(FreeCADMainCmd_SRCS
    ${CMAKE_CURRENT_BINARY_DIR}/freecadCmd.rc
    cadex.ico
    MainCmd.cpp
)

add_executable(FreeCADMainCmd ${FreeCADMainCmd_SRCS})
if(BUILD_TEST)
    add_dependencies(FreeCADMainCmd TestSources)
endif()

SET(FreeCADMainCmd_LIBS
    FreeCADApp
    ${QtCore_LIBRARIES}
    ${QtXml_LIBRARIES}
)

if(NOT BUILD_DYNAMIC_LINK_PYTHON)
    # executables have to be linked against python libraries,
    # because extension modules are not.
    list(APPEND FreeCADMainCmd_LIBS
        ${Python3_LIBRARIES}
    )
endif(NOT BUILD_DYNAMIC_LINK_PYTHON)

target_link_libraries(FreeCADMainCmd
    ${FreeCADMainCmd_LIBS}
)
if (FREECAD_WARN_ERROR)
    target_compile_warn_error(FreeCADMainCmd)
endif()

SET_BIN_DIR(FreeCADMainCmd FreeCADCmd)

if(WIN32)
    INSTALL(TARGETS FreeCADMainCmd
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    )
elseif(APPLE AND NOT BUILD_WITH_CONDA)
    INSTALL(TARGETS FreeCADMainCmd
        RUNTIME DESTINATION MacOS
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    )
else()
    INSTALL(TARGETS FreeCADMainCmd
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
    )
endif()

######################## Cadex portable launchers ########################
if(WIN32)

    add_executable(CadexCmdPortableLauncher
        CadexPortableLauncher.cpp
        ${CMAKE_CURRENT_BINARY_DIR}/cadexCmdPortableLauncher.rc
        cadex.ico
    )
    if(FREECAD_WARN_ERROR)
        target_compile_warn_error(CadexCmdPortableLauncher)
    endif()
    SET_BIN_DIR(CadexCmdPortableLauncher CadexCmdPortableLauncher)
    INSTALL(TARGETS CadexCmdPortableLauncher RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()

######################## FreeCADMainPy ########################

SET(FreeCADMainPy_SRCS
    MainPy.cpp
)

add_library(FreeCADMainPy SHARED ${FreeCADMainPy_SRCS})

target_link_libraries(FreeCADMainPy FreeCADApp)
if (FREECAD_WARN_ERROR)
    target_compile_warn_error(FreeCADMainPy)
endif()

SET_BIN_DIR(FreeCADMainPy FreeCAD)
SET_PYTHON_PREFIX_SUFFIX(FreeCADMainPy)

if(WIN32)
    INSTALL(TARGETS FreeCADMainPy
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    )
else(WIN32)
    INSTALL(TARGETS FreeCADMainPy
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    )
endif(WIN32)
