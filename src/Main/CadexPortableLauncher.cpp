// SPDX-License-Identifier: LGPL-2.1-or-later

#include <windows.h>

#include <cwctype>
#include <cstdio>
#include <string>
#include <vector>

namespace
{

#ifdef CADEX_GUI_LAUNCHER
constexpr wchar_t TargetRelativePath[] = L"bin\\cadex.exe";
#else
constexpr wchar_t TargetRelativePath[] = L"bin\\freecadcmd.exe";
#endif

std::wstring windowsErrorMessage(DWORD error)
{
    wchar_t* buffer = nullptr;
    const DWORD size = FormatMessageW(FORMAT_MESSAGE_ALLOCATE_BUFFER
                                          | FORMAT_MESSAGE_FROM_SYSTEM
                                          | FORMAT_MESSAGE_IGNORE_INSERTS,
                                      nullptr,
                                      error,
                                      MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
                                      reinterpret_cast<wchar_t*>(&buffer),
                                      0,
                                      nullptr);
    std::wstring message;
    if (size != 0 && buffer != nullptr) {
        message.assign(buffer, size);
        LocalFree(buffer);
        while (!message.empty()
               && (message.back() == L'\r' || message.back() == L'\n')) {
            message.pop_back();
        }
    }
    else {
        message = L"Windows error " + std::to_wstring(error);
    }
    return message;
}

void reportError(const std::wstring& message)
{
#ifdef CADEX_GUI_LAUNCHER
    MessageBoxW(nullptr, message.c_str(), L"cadex", MB_OK | MB_ICONERROR);
#else
    std::fwprintf(stderr, L"cadex: %ls\n", message.c_str());
#endif
}

std::wstring executablePath()
{
    // Windows extended-length paths are limited to 32,767 wide characters.
    std::vector<wchar_t> buffer(32768);
    const DWORD size = GetModuleFileNameW(nullptr,
                                          buffer.data(),
                                          static_cast<DWORD>(buffer.size()));
    if (size == 0 || size >= buffer.size()) {
        return {};
    }
    return {buffer.data(), size};
}

const wchar_t* originalArgumentTail()
{
    const wchar_t* cursor = GetCommandLineW();
    while (*cursor != L'\0' && std::iswspace(*cursor)) {
        ++cursor;
    }

    // Preserve the original quoting of every argument after argv[0]. Windows
    // executable paths cannot contain a quote, so the first quoted token can
    // be skipped without reparsing the remainder of the command line.
    if (*cursor == L'"') {
        ++cursor;
        while (*cursor != L'\0' && *cursor != L'"') {
            ++cursor;
        }
        if (*cursor == L'"') {
            ++cursor;
        }
    }
    else {
        while (*cursor != L'\0' && !std::iswspace(*cursor)) {
            ++cursor;
        }
    }
    while (*cursor != L'\0' && std::iswspace(*cursor)) {
        ++cursor;
    }
    return cursor;
}

int launchTarget()
{
    const std::wstring launcher = executablePath();
    const auto separator = launcher.find_last_of(L"\\/");
    if (launcher.empty() || separator == std::wstring::npos) {
        reportError(L"Could not determine the portable cadex directory.");
        return 1;
    }

    const std::wstring root = launcher.substr(0, separator);
    const std::wstring target = root + L"\\" + TargetRelativePath;
    const auto targetSeparator = target.find_last_of(L"\\/");
    const std::wstring workingDirectory = target.substr(0, targetSeparator);
    const DWORD attributes = GetFileAttributesW(target.c_str());
    if (attributes == INVALID_FILE_ATTRIBUTES || (attributes & FILE_ATTRIBUTE_DIRECTORY) != 0) {
        reportError(L"The portable cadex executable is missing:\n" + target);
        return 1;
    }

    std::wstring commandLine = L"\"" + target + L"\"";
    const wchar_t* argumentTail = originalArgumentTail();
    if (*argumentTail != L'\0') {
        commandLine += L" ";
        commandLine += argumentTail;
    }
    std::vector<wchar_t> mutableCommandLine(commandLine.begin(), commandLine.end());
    mutableCommandLine.push_back(L'\0');

    STARTUPINFOW startupInfo {};
    startupInfo.cb = sizeof(startupInfo);
    PROCESS_INFORMATION processInfo {};
    if (!CreateProcessW(target.c_str(),
                        mutableCommandLine.data(),
                        nullptr,
                        nullptr,
                        TRUE,
                        0,
                        nullptr,
                        workingDirectory.c_str(),
                        &startupInfo,
                        &processInfo)) {
        reportError(L"Could not start portable cadex:\n" + windowsErrorMessage(GetLastError()));
        return 1;
    }

    CloseHandle(processInfo.hThread);
#ifdef CADEX_GUI_LAUNCHER
    CloseHandle(processInfo.hProcess);
    return 0;
#else
    const DWORD waitResult = WaitForSingleObject(processInfo.hProcess, INFINITE);
    DWORD exitCode = 1;
    if (waitResult != WAIT_OBJECT_0 || !GetExitCodeProcess(processInfo.hProcess, &exitCode)) {
        reportError(L"Could not read the cadex command-line exit status:\n"
                    + windowsErrorMessage(GetLastError()));
        exitCode = 1;
    }
    CloseHandle(processInfo.hProcess);
    return static_cast<int>(exitCode);
#endif
}

}  // namespace

#ifdef CADEX_GUI_LAUNCHER
int WINAPI wWinMain(HINSTANCE, HINSTANCE, wchar_t*, int)
#else
int wmain()
#endif
{
    return launchTarget();
}
