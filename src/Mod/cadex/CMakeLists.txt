# SPDX-License-Identifier: LGPL-2.1-or-later

set(Cadex_Scripts
    Init.py
    InitGui.py
    CadexAuth.py
    CadexCodex.py
    CadexCore.py
    CadexDebug.py
    CadexEditState.py
    CadexGrid.py
    CadexGeometry.py
    CadexGui.py
    CadexInspection.py
    CadexModelingSurface.py
    CadexPreferences.py
    CadexPromptStarters.py
    CadexProvider.py
    CadexReferenceContracts.py
    CadexProject.py
    CadexParametersPanel.py
    CadexSession.py
    CadexExperimentalChat.py
    CadexExperimentalMode.py
    CadexScriptedEditor.py
    CadexScriptedOwnership.py
    CadexScriptedProcess.py
    CadexScriptedPublication.py
    CadexTools.py
    CadexTransactions.py
    CadexScriptedDomains.py
    CadexScriptedRuntime.py
    CadexScriptedDomainPublication.py
    cadex_assembly_api.py
    cadex_assembly_worker.py
    CadexAssemblyHierarchy.py
    cadex_domain_api.py
    cadex_domain_worker.py
    cadex_part_api.py
    cadex_part_worker.py
    cadex_partdesign_api.py
    cadex_partdesign_worker.py
    cadex_project_api.py
    cadex_project_worker.py
    cadex_sketcher_api.py
    cadex_sketcher_worker.py
    CadexDigest.py
    CadexPointArtifacts.py
    requirements.txt
)

set(Cadex_Resources
    preferences-cadex.svg
    cadex-open-assistant.svg
    cadex-send.svg
    cadex-stop.svg
    cadex-activity.svg
    cadex-attach-image.svg
    cadex-attach-view.svg
    cadex-new-conversation.svg
    cadex-prompt-starters.svg
)

file(GLOB_RECURSE Cadex_ToolImplScripts
    CONFIGURE_DEPENDS
    RELATIVE ${CMAKE_CURRENT_SOURCE_DIR}
    tool_impl/*.py
)

add_custom_target(CadexScripts ALL
    SOURCES ${Cadex_Scripts} ${Cadex_ToolImplScripts} ${Cadex_Resources}
)

fc_target_copy_resource(CadexScripts
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_BINARY_DIR}/Mod/cadex
    ${Cadex_Scripts}
    ${Cadex_ToolImplScripts}
    ${Cadex_Resources}
)

install(
    FILES
        ${Cadex_Scripts}
        ${Cadex_Resources}
    DESTINATION
        Mod/cadex
)

install(
    DIRECTORY
        tool_impl
    DESTINATION
        Mod/cadex
    FILES_MATCHING
        PATTERN "*.py"
)

add_executable(CadexGeometryWorker
    CadexGeometryWorker.cpp
)

target_include_directories(CadexGeometryWorker
    PRIVATE
        ${OCC_INCLUDE_DIR}
        ${nlohmann_json_INCLUDE_DIRS}
)

target_link_directories(CadexGeometryWorker
    PRIVATE
        ${OCC_LIBRARY_DIR}
)

target_link_libraries(CadexGeometryWorker
    PRIVATE
        ${OCC_LIBRARIES}
        ${OCC_DEBUG_LIBRARIES}
)

if(FREECAD_WARN_ERROR)
    target_compile_warn_error(CadexGeometryWorker)
endif()

SET_BIN_DIR(CadexGeometryWorker CadexGeometryWorker)

install(
    TARGETS CadexGeometryWorker
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
