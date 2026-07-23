// SPDX-License-Identifier: LGPL-2.1-or-later

// The bundle copies this build output to its user-facing root filename.
IDI_ICON1 ICON DISCARDABLE "cadex.ico"

1 VERSIONINFO
FILEVERSION ${PACKAGE_VERSION_MAJOR},${PACKAGE_VERSION_MINOR},${PACKAGE_VERSION_PATCH},${PACKAGE_BUILD_VERSION}
PRODUCTVERSION ${PACKAGE_VERSION_MAJOR},${PACKAGE_VERSION_MINOR},${PACKAGE_VERSION_PATCH},${PACKAGE_BUILD_VERSION}
FILEFLAGSMASK 0x3fL
#ifdef _DEBUG
FILEFLAGS 0x1L
#else
FILEFLAGS 0x0L
#endif
FILEOS 0x40004L
FILETYPE 0x1L
FILESUBTYPE 0x0L
BEGIN
    BLOCK "StringFileInfo"
    BEGIN
        BLOCK "040904b0"
        BEGIN
            VALUE "CompanyName", "cadex Project"
            VALUE "FileDescription", "${CADEX_LAUNCHER_DESCRIPTION}"
            VALUE "FileVersion", "${PACKAGE_VERSION}${PACKAGE_VERSION_SUFFIX}"
            VALUE "InternalName", "${CADEX_LAUNCHER_FILENAME}"
            VALUE "LegalCopyright", "Copyright (C) FreeCAD and cadex contributors"
            VALUE "OriginalFilename", "${CADEX_LAUNCHER_FILENAME}"
            VALUE "ProductName", "cadex"
            VALUE "ProductVersion", "${PACKAGE_VERSION}${PACKAGE_VERSION_SUFFIX}"
        END
    END
    BLOCK "VarFileInfo"
    BEGIN
        VALUE "Translation", 0x409, 1200
    END
END
