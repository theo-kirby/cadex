@echo on

@REM CI forwards CCACHE_DIR to a persisted cache directory; local builds get an
@REM empty value from the recipe, so drop it and let ccache use its own default.
if "%CCACHE_DIR%"=="" set "CCACHE_DIR="

@REM When CI provides a persisted ccache, normalize the per-run rattler-build work
@REM path so MSVC object hashes stay stable across runs (otherwise every file is a
@REM cache miss because cl.exe bakes absolute paths into the hash, unlike GCC/Clang
@REM which conda auto-configures with -ffile-prefix-map). CCACHE_BASEDIR rewrites
@REM absolute paths under the build root to relative form; the sloppiness flags
@REM tolerate freshly-copied source timestamps and precompiled headers.
if not "%CCACHE_DIR%"=="" for %%I in ("%SRC_DIR%\..") do set "CCACHE_BASEDIR=%%~fI"
if not "%CCACHE_DIR%"=="" set "CCACHE_SLOPPINESS=pch_defines,time_macros,include_file_ctime,include_file_mtime,locale"

@REM Zero ccache stats up front so the end-of-build dump reflects only this build.
if not "%CCACHE_DIR%"=="" ccache -z >nul 2>&1

@REM :: free up extra disk space, compare
@REM :: https://github.com/conda-forge/conda-smithy/issues/1949
@REM rmdir /s /q C:\hostedtoolcache\windows

@REM set "CFLAGS= "
@REM set "CXXFLAGS= -DBOOST_PROGRAM_OPTIONS_DYN_LINK=1"
@REM set "LDFLAGS_SHARED= ucrt.lib"

set "CMAKE_GENERATOR="
set "CMAKE_GENERATOR_PLATFORM="

cmake ^
    %CMAKE_ARGS% ^
    --preset conda-windows-release ^
    -D CMAKE_C_COMPILER:STRING="%CC%" ^
    -D CMAKE_CXX_COMPILER:STRING="%CXX%" ^
    -D CMAKE_INCLUDE_PATH:FILEPATH="%LIBRARY_PREFIX%/include" ^
    -D CMAKE_INSTALL_LIBDIR:FILEPATH="%LIBRARY_PREFIX%/lib" ^
    -D CMAKE_INSTALL_PREFIX:FILEPATH="%LIBRARY_PREFIX%" ^
    -D CMAKE_LIBRARY_PATH:FILEPATH="%LIBRARY_PREFIX%/lib" ^
    -D CMAKE_PREFIX_PATH:FILEPATH="%LIBRARY_PREFIX%" ^
    -D INSTALL_TO_SITEPACKAGES:BOOL=ON ^
    -D OCC_INCLUDE_DIR:FILEPATH="%LIBRARY_PREFIX%/include/opencascade" ^
    -D OCC_LIBRARY_DIR:FILEPATH="%LIBRARY_PREFIX%/lib" ^
    -D Python_EXECUTABLE:FILEPATH="%PYTHON%" ^
    -D Python3_EXECUTABLE:FILEPATH="%PYTHON%" ^
    -D SMESH_INCLUDE_DIR:FILEPATH="%LIBRARY_PREFIX%/include/smesh" ^
    -D SMESH_LIBRARY:FILEPATH="%LIBRARY_PREFIX%/lib/SMESH.lib" ^
    -D ENABLE_DEVELOPER_TESTS:BOOL=OFF ^
    -B build ^
    -S .
if %ERRORLEVEL% neq 0 exit 1

ninja -C build install
if %ERRORLEVEL% neq 0 exit 1

@REM Report ccache effectiveness for this build (hit/miss ratio).
if not "%CCACHE_DIR%"=="" ccache -s

ren %LIBRARY_PREFIX%\bin\FreeCAD.exe freecad.exe
ren %LIBRARY_PREFIX%\bin\FreeCADCmd.exe freecadcmd.exe
