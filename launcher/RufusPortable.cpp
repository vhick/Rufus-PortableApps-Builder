// Rufus PortableApps launcher. GNU GPL v3-or-later, independent project.
// Rufus's native INI mode stores files beside its process executable.
// Put a verified copy of the official signed Rufus binary inside Data/Runtime so
// the actual application and every app-relative write live inside portable Data.
// Host-level disk/USB/system operations are intentionally NOT intercepted.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <wincrypt.h>
#include <filesystem>
#include <string>
#include <vector>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <system_error>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <cctype>
#pragma comment(lib, "Shell32.lib")
#pragma comment(lib, "Advapi32.lib")
namespace fs = std::filesystem;
using String = std::wstring;

static void error(const String& s) { MessageBoxW(nullptr, s.c_str(), L"Rufus Portable - Safe Startup", MB_OK | MB_ICONERROR); }
static String module_path() {
    std::vector<wchar_t> buf(32768);
    DWORD size = GetModuleFileNameW(nullptr, buf.data(), static_cast<DWORD>(buf.size()));
    if (!size || size >= buf.size()) return {};
    return String(buf.data(), size);
}
static bool is_reparse(const fs::path& p) {
    DWORD a = GetFileAttributesW(p.c_str());
    return a != INVALID_FILE_ATTRIBUTES && (a & FILE_ATTRIBUTE_REPARSE_POINT) != 0;
}
static bool ensure_directories_no_links(const fs::path& root, const std::vector<fs::path>& paths) {
    for (const auto& p : paths) {
        fs::path current = root;
        if (is_reparse(current)) return false;
        for (const auto& part : p) {
            current /= part;
            if (fs::exists(current) && is_reparse(current)) return false;
            std::error_code ec;
            fs::create_directory(current, ec);
            if (ec && !fs::is_directory(current)) return false;
        }
    }
    return true;
}
static std::vector<BYTE> sha256(const fs::path& path) {
    HCRYPTPROV prov = 0;
    HCRYPTHASH hash = 0;
    if (!CryptAcquireContextW(&prov, nullptr, nullptr, PROV_RSA_AES, CRYPT_VERIFYCONTEXT)) return {};
    if (!CryptCreateHash(prov, CALG_SHA_256, 0, 0, &hash)) { CryptReleaseContext(prov, 0); return {}; }
    HANDLE f = CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (f == INVALID_HANDLE_VALUE) { CryptDestroyHash(hash); CryptReleaseContext(prov, 0); return {}; }
    std::vector<BYTE> block(65536);
    DWORD count = 0;
    bool ok = true;
    while (true) {
        if (!ReadFile(f, block.data(), static_cast<DWORD>(block.size()), &count, nullptr)) { ok = false; break; }
        if (count == 0) break;
        if (!CryptHashData(hash, block.data(), count, 0)) { ok = false; break; }
    }
    CloseHandle(f);
    std::vector<BYTE> result(32);
    DWORD length = static_cast<DWORD>(result.size());
    if (!ok || !CryptGetHashParam(hash, HP_HASHVAL, result.data(), &length, 0) || length != 32) result.clear();
    CryptDestroyHash(hash);
    CryptReleaseContext(prov, 0);
    return result;
}
static std::string hex_sha(const std::vector<BYTE>& hash) {
    const char digits[] = "0123456789abcdef";
    std::string out;
    for (BYTE b : hash) { out.push_back(digits[b >> 4]); out.push_back(digits[b & 15]); }
    return out;
}
static bool matches_packaged_hash(const fs::path& vendor, const fs::path& checksum) {
    std::ifstream stream(checksum);
    std::string expected;
    if (!(stream >> expected) || expected.size() != 64) return false;
    for (char& c : expected) {
        if (!std::isxdigit(static_cast<unsigned char>(c))) return false;
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    const auto actual = sha256(vendor);
    return actual.size() == 32 && hex_sha(actual) == expected;
}
static bool same_contents(const fs::path& a, const fs::path& b) {
    std::error_code ec;
    if (!fs::exists(b) || fs::file_size(a, ec) != fs::file_size(b, ec) || ec) return false;
    const auto h1 = sha256(a), h2 = sha256(b);
    return h1.size() == 32 && h1 == h2;
}
static String quote(const String& arg) {
    // Correct Windows CommandLineToArgvW-compatible argument quoting.
    if (arg.find_first_of(L" \t\n\v\"") == String::npos) return arg;
    String out = L"\"";
    size_t slashes = 0;
    for (wchar_t c : arg) {
        if (c == L'\\') { ++slashes; continue; }
        if (c == L'\"') {
            out.append(slashes * 2 + 1, L'\\'); out.push_back(c);
        } else {
            out.append(slashes, L'\\'); out.push_back(c);
        }
        slashes = 0;
    }
    out.append(slashes * 2, L'\\');
    out.push_back(L'\"');
    return out;
}
static bool atomic_write(const fs::path& dest, const std::string& text) {
    fs::path temp = dest.wstring() + L".new";
    HANDLE h = CreateFileW(temp.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) return false;
    DWORD written = 0;
    bool ok = WriteFile(h, text.data(), static_cast<DWORD>(text.size()), &written, nullptr) && written == text.size();
    ok = FlushFileBuffers(h) && ok;
    CloseHandle(h);
    if (!ok) return false;
    return MoveFileExW(temp.c_str(), dest.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
}
static std::string utf8(const String& s) {
    int n = WideCharToMultiByte(CP_UTF8, 0, s.c_str(), static_cast<int>(s.size()), nullptr, 0, nullptr, nullptr);
    if (n <= 0) return {};
    std::string out(n, '\0');
    WideCharToMultiByte(CP_UTF8, 0, s.c_str(), static_cast<int>(s.size()), &out[0], n, nullptr, nullptr);
    return out;
}
static bool snapshot(const fs::path& folder, const fs::path& manifest) {
    // Contains all files and *also all empty directories*, preserving relative paths.
    std::ostringstream report;
    report << "TraceGuard runtime inventory v1\n";
    std::error_code ec;
    for (auto it = fs::recursive_directory_iterator(folder, fs::directory_options::none, ec); !ec && it != fs::recursive_directory_iterator(); it.increment(ec)) {
        const fs::path rel = fs::relative(it->path(), folder, ec);
        if (ec || is_reparse(it->path())) return false; // do not follow junctions/symlinks
        if (it->is_directory(ec)) report << "DIR\t" << utf8(rel.wstring()) << "\n";
        else if (it->is_regular_file(ec)) report << "FILE\t" << utf8(rel.wstring()) << "\n";
        else return false;
        if (ec) return false;
    }
    if (ec) return false;
    return atomic_write(manifest, report.str());
}
static std::string now_stamp() {
    SYSTEMTIME st; GetSystemTime(&st);
    char buffer[64];
    sprintf_s(buffer, "%04u%02u%02uT%02u%02u%02uZ", static_cast<unsigned>(st.wYear), static_cast<unsigned>(st.wMonth), static_cast<unsigned>(st.wDay),
              static_cast<unsigned>(st.wHour), static_cast<unsigned>(st.wMinute), static_cast<unsigned>(st.wSecond));
    return buffer;
}
static String wide_stamp() {
    const std::string stamp = now_stamp();
    return String(stamp.begin(), stamp.end());
}
static bool backup_config(const fs::path& config, const fs::path& backupdir) {
    if (!fs::exists(config)) return true;
    const fs::path destination = backupdir / (L"rufus-" + wide_stamp() + L".ini");
    // Fail closed rather than replacing a previous backup.
    return CopyFileW(config.c_str(), destination.c_str(), TRUE) != 0;
}
static unsigned long long fnv1a(const String& s) {
    unsigned long long h = 14695981039346656037ull;
    for (wchar_t w : s) { h ^= static_cast<unsigned long long>(w); h *= 1099511628211ull; }
    return h;
}
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    const fs::path me(module_path());
    if (me.empty()) { error(L"Unable to locate portable launcher."); return 2; }
    const fs::path root = me.parent_path();
    const fs::path vendor = root / L"App" / L"Rufus" / L"rufus.exe";
    if (!fs::is_regular_file(vendor) || is_reparse(root) || is_reparse(root / L"App") ||
        is_reparse(root / L"App" / L"Rufus") || is_reparse(vendor)) {
        error(L"Official Rufus executable is missing or is a link. Reinstall App files without deleting Data."); return 3;
    }
    if (!matches_packaged_hash(vendor, root / L"App" / L"Rufus" / L"rufus.sha256")) {
        error(L"Rufus payload failed the builder's SHA256 check. Do not launch an altered executable; reinstall App without deleting Data."); return 3;
    }
    std::wostringstream mutexname;
    mutexname << L"Local\\RufusPortable-" << std::hex << fnv1a(root.wstring());
    HANDLE mutex = CreateMutexW(nullptr, TRUE, mutexname.str().c_str());
    if (!mutex || GetLastError() == ERROR_ALREADY_EXISTS) {
        if (mutex) CloseHandle(mutex);
        error(L"Another instance of this PortableApps launcher is in use. Close Rufus before trying again."); return 4;
    }
    int status = 5;
    do {
        if (!ensure_directories_no_links(root, {L"Data", L"Data\\Runtime", L"Data\\TraceGuard", L"Data\\TraceGuard\\Backups"})) {
            error(L"Data is not writable, or a protected directory is a symbolic link. No files were removed."); break;
        }
        const fs::path runtime = root / L"Data" / L"Runtime";
        const fs::path target = runtime / L"rufus.exe";
        const fs::path config = runtime / L"rufus.ini";
        const fs::path trace = root / L"Data" / L"TraceGuard";
        const fs::path journal = trace / L"active-session.txt";
        if (is_reparse(runtime) || is_reparse(target) || is_reparse(config) || is_reparse(journal)) {
            error(L"Protected portable data points to a link. Refusing to modify it."); break;
        }
        if (!fs::exists(config)) {
            HANDLE h = CreateFileW(config.c_str(), GENERIC_WRITE, FILE_SHARE_READ, nullptr, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
            if (h == INVALID_HANDLE_VALUE) { error(L"Cannot initialize portable rufus.ini inside Data."); break; }
            CloseHandle(h);
        }
        // If launcher crashed previously, all data was already written to Data/Runtime.
        // Keep session journal as evidence; do not delete, restore or move user files.
        if (fs::exists(journal)) {
            const fs::path recovery = trace / (L"recovered-session-" + wide_stamp() + L".txt");
            if (!MoveFileExW(journal.c_str(), recovery.c_str(), MOVEFILE_WRITE_THROUGH)) {
                error(L"Previous launch journal could not be preserved; recovery needs manual attention."); break;
            }
        }
        if (!same_contents(vendor, target)) {
            if (fs::exists(target) && !backup_config(config, trace / L"Backups")) {
                error(L"Cannot back up existing Rufus settings before an application update."); break;
            }
            const fs::path temp = runtime / L"rufus.exe.new";
            if (is_reparse(temp) || !CopyFileW(vendor.c_str(), temp.c_str(), FALSE) || !same_contents(vendor, temp)) {
                error(L"Cannot stage a verified executable in Data. Existing executable and settings were preserved."); break;
            }
            if (!MoveFileExW(temp.c_str(), target.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
                error(L"Cannot activate new Rufus binary. Close any existing Rufus processes before updating."); break;
            }
        }
        if (!atomic_write(journal, "start=" + now_stamp() + "\napplication=Data/Runtime/rufus.exe\nsettings=Data/Runtime/rufus.ini\n")) {
            error(L"Could not create crash recovery journal in Data."); break;
        }
        int argc = 0;
        LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
        String params;
        if (argv) {
            for (int i = 1; i < argc; ++i) { if (!params.empty()) params += L" "; params += quote(argv[i]); }
            LocalFree(argv);
        }
        SHELLEXECUTEINFOW launch{};
        launch.cbSize = sizeof(launch);
        launch.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_FLAG_NO_UI;
        launch.lpVerb = L"open";
        launch.lpFile = target.c_str();
        launch.lpParameters = params.empty() ? nullptr : params.c_str();
        launch.lpDirectory = runtime.c_str();
        launch.nShow = SW_SHOWNORMAL;
        if (!ShellExecuteExW(&launch) || !launch.hProcess) {
            error(L"Rufus failed to start. Its settings remain safely in Data/Runtime. Windows UAC may be required."); break;
        }
        const DWORD wait = WaitForSingleObject(launch.hProcess, INFINITE);
        DWORD exit_code = 1;
        bool valid = wait == WAIT_OBJECT_0 && GetExitCodeProcess(launch.hProcess, &exit_code);
        CloseHandle(launch.hProcess);
        if (!valid || !snapshot(runtime, trace / L"runtime-inventory.tsv")) {
            error(L"Rufus ended but runtime inventory could not be saved. Data was not deleted. Review TraceGuard journal."); break;
        }
        if (!DeleteFileW(journal.c_str())) {
            error(L"Data is safe, but the TraceGuard session journal could not be cleared."); break;
        }
        status = static_cast<int>(exit_code);
    } while (false);
    ReleaseMutex(mutex); CloseHandle(mutex);
    return status;
}
