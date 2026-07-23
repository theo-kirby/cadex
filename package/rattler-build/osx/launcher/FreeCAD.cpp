#include <cerrno>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#include <mach-o/dyld.h>
#include <unistd.h>

namespace {

std::filesystem::path executablePath()
{
    uint32_t size = 0;
    if (_NSGetExecutablePath(nullptr, &size) != -1 || size == 0) {
        throw std::runtime_error("Could not determine the VibeCAD launcher path.");
    }

    std::vector<char> buffer(size);
    if (_NSGetExecutablePath(buffer.data(), &size) != 0) {
        throw std::runtime_error("Could not read the VibeCAD launcher path.");
    }
    return std::filesystem::canonical(buffer.data());
}

std::map<std::string, std::string> environment(char* const* envp)
{
    std::map<std::string, std::string> result;
    for (std::size_t index = 0; envp[index] != nullptr; ++index) {
        const std::string entry(envp[index]);
        const auto separator = entry.find('=');
        if (separator == std::string::npos) {
            continue;
        }
        result[entry.substr(0, separator)] = entry.substr(separator + 1);
    }
    return result;
}

std::vector<char*> mutablePointers(std::vector<std::string>& values)
{
    std::vector<char*> pointers;
    pointers.reserve(values.size() + 1);
    for (auto& value : values) {
        pointers.push_back(value.data());
    }
    pointers.push_back(nullptr);
    return pointers;
}

} // namespace

int main(int argc, char* argv[], char* const* envp)
{
    try {
        const auto launcher = executablePath();
        const auto resources = std::filesystem::canonical(
            launcher.parent_path() / ".." / "Resources");
        const bool launcherSmoke = argc == 2
            && std::strcmp(argv[1], "--vibecad-launcher-smoke") == 0;
        const char* runtimeName = launcherSmoke ? "freecadcmd" : "freecad";
        const auto runtime = resources / "bin" / runtimeName;
        if (!std::filesystem::is_regular_file(runtime)) {
            std::cerr << "VibeCAD runtime executable is missing: " << runtime << '\n';
            return 1;
        }

        auto env = environment(envp);
        const auto prefix = resources.string();
        env["PREFIX"] = prefix;
        env["LD_LIBRARY_PATH"] = prefix + "/lib";
        env["PYTHONPATH"] = prefix;
        env["PYTHONHOME"] = prefix;
        env["FONTCONFIG_FILE"] = "/etc/fonts/fonts.conf";
        env["FONTCONFIG_PATH"] = "/etc/fonts";
        env["LANG"] = "UTF-8";
        env["SSL_CERT_FILE"] = prefix + "/ssl/cacert.pem";
        env["GIT_SSL_CAINFO"] = prefix + "/ssl/cacert.pem";

        std::vector<std::string> environmentStorage;
        environmentStorage.reserve(env.size());
        for (const auto& [name, value] : env) {
            environmentStorage.push_back(name + '=' + value);
        }
        auto environmentPointers = mutablePointers(environmentStorage);

        std::vector<std::string> argumentStorage;
        argumentStorage.reserve(
            launcherSmoke ? 3U : static_cast<std::size_t>(argc));
        argumentStorage.push_back(runtime.string());
        if (launcherSmoke) {
            argumentStorage.emplace_back("--safe-mode");
            argumentStorage.emplace_back("--version");
        }
        else {
            for (int index = 1; index < argc; ++index) {
                argumentStorage.emplace_back(argv[index]);
            }
        }
        auto argumentPointers = mutablePointers(argumentStorage);

        execve(
            runtime.c_str(),
            argumentPointers.data(),
            environmentPointers.data());
        std::cerr << "Could not launch the VibeCAD runtime: " << std::strerror(errno)
                  << '\n';
        return 1;
    }
    catch (const std::exception& error) {
        std::cerr << "VibeCAD launcher failed: " << error.what() << '\n';
        return 1;
    }
}
