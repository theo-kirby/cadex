# SPDX-License-Identifier: LGPL-2.1-or-later

set(Cadex_Scripts
    Init.py
    CadexEngineSettings.py
    CadexInspection.py
    CadexModelingSurface.py
    CadexPinResolution.py
    CadexReferenceContracts.py
    CadexRouting.py
    CadexBundle.py
    CadexDynamics.py
    CadexProject.py
    CadexScriptStore.py
    CadexSubshapeQuery.py
    CadexScriptedOwnership.py
    CadexScriptedProcess.py
    CadexScriptedPublication.py
    CadexTools.py
    CadexScriptedDomains.py
    CadexScriptedRuntime.py
    CadexScriptedDomainPublication.py
    CadexWarmWorker.py
    cadex_assembly_api.py
    cadex_assembly_worker.py
    cadex_domain_api.py
    cadex_domain_worker.py
    cadex_mesh_api.py
    cadex_mesh_worker.py
    cadex_part_api.py
    cadex_part_worker.py
    cadex_partdesign_api.py
    cadex_partdesign_worker.py
    cadex_project_api.py
    cadex_preview_worker.py
    cadex_project_worker.py
    cadex_rebuild.py
    cadex_sketcher_api.py
    cadex_sketcher_worker.py
    cadex_tessellation.py
    cadexd.py
    CadexdProtocol.py
    CadexDigest.py
)


add_custom_target(CadexScripts ALL
    SOURCES ${Cadex_Scripts}
)

fc_target_copy_resource(CadexScripts
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_BINARY_DIR}/Mod/cadex
    ${Cadex_Scripts}
   
   
)

install(
    FILES
        ${Cadex_Scripts}
       
    DESTINATION
        Mod/cadex
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
