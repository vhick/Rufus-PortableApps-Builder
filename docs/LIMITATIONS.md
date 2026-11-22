# Known constraints and maintenance decisions

1. This kit **does not rebuild Rufus from source**; it acquires upstream signed binary releases. That is an explicit, verified strategy designed to reduce maintenance, build cost and signing risks. Source code is retrieved and audited separately at the exact stable release tag. No upstream app dependency or compiler updates are needed for this acquisition path.
2. Supports the **official stable Windows x64 portable EXE** only. If Rufus releases only a different architecture or removes portable builds, the builder fails rather than publishing mislabeled output.
3. Rufus is a system/USB tool. Some of its intended features alter disks, Windows mount information or other host state. These effects cannot all be made portable or reverted safely. TraceGuard scope is limited to app-owned Data/Runtime and explicitly known evidence. Claiming zero host traces would be inaccurate.
4. The official Rufus executable retains its upstream signature; `RufusPortable.exe` is a newly compiled, **unsigned**, independent launcher. Unsigned new executables may draw Windows SmartScreen warnings. We make no antivirus-evasion claims.
5. Manual GUI/UI and real hardware acceptance are required. Running real Rufus write operations in unattended GitHub Actions would be unsafe.
6. Windows GitHub-hosted runner images vary. The kit searches installed Visual Studio MSVC toolchain dynamically but fails clearly if no supported compiler exists. It does not install arbitrary compilers.
7. `config/known-good.json` starts uninitialized. The published release ZIP manifest and publisher checksums are the durable source of truth. Automatic source-repo commits are intentionally disabled.
8. Shared packager `v1.0.0` and publisher `v1.1.1` remain pinned. Maintenance flags new tags but never adopts unverified action versions.
9. Reproducible binary identity is recorded through official asset SHA256, source commit, compiler detection and package metadata. Without separately pinned Windows runner images/compiler builds, full byte-for-byte reconstruction of the compiled launcher across years is not guaranteed.
10. A malicious or corrupt Windows install, a malicious administrator, or mutable upstream release assets cannot be eliminated by this architecture. Signatures and strict release origins materially reduce these risks.
11. No guaranteed rollback across new Rufus profile migrations. The launcher backs up INI before binary change; users still need backups of all Data before switching major versions.
12. `official` packaging engine is only a conditional, explicitly selected experimental attempt. It may not work on some PortableApps.com Installer versions. The community installer is independently generated and not officially certified.
13. The first GitHub Actions run is **not confirmed** until logs are examined; local tests cannot replace Windows runner testing.
