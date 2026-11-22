// Non-destructive synthetic program for testing the real compiled launcher.
#include <windows.h>
#include <filesystem>
#include <fstream>
#include <string>
namespace fs = std::filesystem;
#ifndef TEST_VERSION
#define TEST_VERSION 1
#endif
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    wchar_t buf[32768] = {};
    GetModuleFileNameW(nullptr, buf, 32768);
    const fs::path folder = fs::path(buf).parent_path();
    if (!fs::exists(folder / L"rufus.ini")) return 11;
    std::ofstream output(folder / "data-created.txt", std::ios::app);
    if (!output) return 12;
    output << "fixture " << TEST_VERSION << "\n";
    output.close();
    fs::create_directories(folder / "empty-folder" / "nested-empty");
    std::ofstream ini(folder / "rufus.ini", std::ios::app);
    if (!ini) return 13;
    ini << "fixture_version=" << TEST_VERSION << "\n";
    return 0;
}
