// SPDX-License-Identifier: LGPL-2.1-or-later
/////////////////////////////////////////////////////////////////////////////
// For info about the file structrure see
// https://docs.microsoft.com/en-us/windows/win32/menurc/versioninfo-resource
// and
// https://docs.microsoft.com/en-us/windows/win32/menurc/stringfileinfo-block

// Icon
//
// Icon with lowest ID value placed first to ensure application icon
// remains consistent on all systems.
IDI_ICON1               ICON    DISCARDABLE     "cadex.ico"

// File info for the FreeCADCmd.exe
//
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
        BLOCK "040904b0" // 409 stands for US English
        BEGIN
            VALUE "CompanyName", "cadex Project"
            VALUE "FileDescription", "cadex command line executable"
            VALUE "FileVersion", "${PACKAGE_VERSION}${PACKAGE_VERSION_SUFFIX}"
            VALUE "InternalName", "FreeCADCmd.exe"
            VALUE "LegalCopyright", "Copyright (C) FreeCAD and cadex contributors"
            VALUE "OriginalFilename", "FreeCADCmd.exe"
            VALUE "ProductName", "cadex"
            VALUE "ProductVersion", "${PACKAGE_VERSION}${PACKAGE_VERSION_SUFFIX}"
        END
    END
    BLOCK "VarFileInfo"
    BEGIN
        VALUE "Translation", 0x409, 1200 //US English, Unicode
    END
END
