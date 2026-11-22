# Rufus source-based portability audit (2026-11-22)

## Evidence, verified at source / official documentation

- **Language/build:** Native Windows C/C++; official upstream documents Visual Studio and MinGW builds with `rufus.sln`, `configure` and `make`. Rufus 4.16 is the current stable release (2026-11-17). Source compilation has significant platform/dependency complexity that is *unnecessary* for redistributing official stable, signed Rufus.
- **Native portable settings:** `res/rufus.ini` says an existing `rufus.ini` beside the launched binary causes settings to be written there, rather than normal registry settings. `src/rufus.c` contains `ini_flags` / filename-`p` logic to cause portable INI creation for the upstream portable variant. Source lines around 3382 of v4.16 show that behavior.
- **Normal-mode registry:** the official FAQ says normal settings use the registry and specifically emphasizes that portable apps can still interact with registry or system areas. Rufus's `src/settings.h` explicitly describes settings access via registry or INI. Historic registry key documented by Rufus: `HKEY_CURRENT_USER\Software\Akeo Consulting\Rufus` for settings such as `IgnoreUsb01`–`IgnoreUsb08`, in non-INI configuration.
- **Other files:** Rufus can download resources, launch helpers, and perform drive/image operations. Whether a particular release places cache, log or downloaded ISO files outside the executable folder depends on the operation and source. Do not assume app-local INI controls every trace.
- **Local group policy:** sample INI documents `DisableLGP` for older behavior. Rufus 4.16's release notes explicitly say they dropped their former Group Policy workaround for Windows format prompts. This is not evidence of zero other Windows host changes.
- **Elevated operations:** disk and USB write operations frequently request elevation; a portable wrapper must not suppress UAC or block the intended behavior.
- **Digital signature:** upstream FAQ says official Rufus executables are Authenticode signed under `Akeo Consulting`. Verify signer, Status=Valid, embedded product version, x64 PE and local SHA256. A local SHA256 alone proves repeatability but not signer identity.
- **License:** Rufus is GPLv3-or-later. The source license is included with every package. This independent redistribution is not endorsed by Rufus or PortableApps.com.

## Intentional data architecture

| Location | Role | Policy |
| --- | --- | --- |
| `RufusPortable.exe` | Compiled signed? **No**, independent unsigned C++ launcher | Root PortableApps menu entry; non-elevated until Rufus requests privilege |
| `App/Rufus/rufus.exe` | Exact signed official upstream asset | Read-only package payload; not a persistent storage location |
| `Data/Runtime/rufus.exe` | Verified copy of official executable | Actual runtime process location; updated by SHA comparison |
| `Data/Runtime/rufus.ini` | Rufus native settings | Direct, crash-resilient persistent storage |
| `Data/Runtime/*` | Other application-relative files/folders | Retained, with directory inventory including empty trees |
| `Data/TraceGuard/active-session.txt` | Startup journal | On crash next launch preserves prior journal as recovered record |
| `Data/TraceGuard/runtime-inventory.tsv` | Filesystem inventory | Includes files and completely empty nested directories |
| `Data/TraceGuard/Backups/rufus-*.ini` | Snapshot before payload version change | Retained during upgrades and downgrades |

The source contract audit is *conservative*: before adopting a new upstream release, it checks the actual release-tagged source for the INI documentation and implementation semantics. It does not pretend that keyword checks replace manual regression testing on every possible Windows release.

## TraceGuard scope and host limitations

TraceGuard records app-relative Data files, avoids unowned host areas, detects reparse points and stale session journals, and protects INI settings during binary replacement. **It does not import arbitrary TEMP, registry, browser profile, ProgramData or AppData writes**. Windows OS changes, USB formatting, mount state, device access and intentional downloaded output are outside the recoverable application profile, may require admin, and may leave host traces. Capturing all of them would risk destruction or corruption of unrelated user data.

**WARNING:** If you store the portable package on a USB disk and then select that same disk for formatting in Rufus, you can destroy your own PortableApps directory. Keep the application on a different disk from the target device.

## Source audit authoritative links

- https://github.com/pbatard/rufus/blob/v4.16/src/rufus.c
- https://github.com/pbatard/rufus/blob/v4.16/res/rufus.ini
- https://github.com/pbatard/rufus/wiki/FAQ
- https://github.com/pbatard/rufus/releases/tag/v4.16
