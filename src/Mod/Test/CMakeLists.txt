# Modified by the Cadex project, 2026. See docs/FREECAD.md.
# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Joao Matos
# SPDX-FileNotice: Part of the FreeCAD project.

SET(Test_SRCS
    __init__.py
    Init.py
    BaseTests.py
    AutoSaverStress.py
    RunAutoSaverStress.py
    Document.py
    Metadata.py
    StringHasher.py
    Recompute.py
    TestApp.py
    UnicodeTests.py
    UnitTests.py
    testmakeWireString.py
    TestPythonSyntax.py
    TestPerf.py
)

SET(TestData_SRCS
    TestData/basic_metadata.xml
    TestData/bad_root_node.xml
    TestData/bad_xml.xml
    TestData/bad_version.xml
    TestData/content_items.xml
    TestData/DXFSample.dxf
)

SOURCE_GROUP("" FILES ${Test_SRCS} ${TestData_SRCS})


set(Test_COPY_OUTPUTS)
foreach(test_src ${Test_SRCS})
    list(APPEND Test_COPY_OUTPUTS "${CMAKE_BINARY_DIR}/Mod/Test/${test_src}")
endforeach()
foreach(test_data_src ${TestData_SRCS})
    list(APPEND Test_COPY_OUTPUTS "${CMAKE_BINARY_DIR}/Mod/Test/${test_data_src}")
endforeach()

add_custom_target(TestSources DEPENDS ${Test_COPY_OUTPUTS})

ADD_CUSTOM_TARGET(Test ALL
    DEPENDS TestSources
    SOURCES ${Test_SRCS} ${TestData_SRCS}
)

fc_copy_sources(Test "${CMAKE_BINARY_DIR}/Mod/Test" ${Test_SRCS} ${TestData_SRCS})

INSTALL(
    FILES
        ${Test_SRCS}
    DESTINATION
        Mod/Test
)

INSTALL(
    FILES
        ${TestData_SRCS}
    DESTINATION
        Mod/Test/TestData
)
