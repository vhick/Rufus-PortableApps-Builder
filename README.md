# Rufus PortableApps Independent Builder b1r1

A standalone GitHub Actions builder for **official, digitally signed stable Rufus releases**. It creates a real `RufusPortable.exe` Windows C++ launcher, an independently validated `RufusPortable_*.zip`, and a separately identified independent NSIS `.paf.exe` installer using your existing pinned shared packager. The validated packages can be published with your pinned shared Release Publisher. The metadata targets PortableApps.com Format 3.9 (2026-03-02).

**Important status:** The source and script fixtures were constructed offline. A real Windows GitHub Actions run, actual signature check, launcher compilation, installer production, and safe manual Rufus GUI acceptance test must still be completed. Do not claim this kit or an unknown future Rufus release has already passed those stages.

## Why this design?

Rufus officially supports native portable mode: an existing `rufus.ini` located **beside the Rufus binary** causes settings to be stored there instead of Rufus' normal registry-based settings. The downloadable `rufus-4.16p.exe` is a portable configuration variant, not a separate engine. We acquire the authentic, signed x64 release executable instead of recompiling upstream dependencies. We DO compile only our **own** C++ launcher.

**Rufus is a disk utility, not a sandbox.** Its intended behavior can include elevated access, partition changes, drive formatting, downloading boot resources, removable-device operations and Windows system effects. No safe PortableApps launcher can promise to reverse a deliberately formatted disk or trap every Windows trace. Never run this kit's CI tests against a physical device automatically.

## What the launcher does

`RufusPortable.exe`:

1. Locates `App/Rufus/rufus.exe` relative to its own position. This is the unchanged, signed official Rufus executable.
2. Creates `Data/Runtime/rufus.ini` *before* Rufus launches.
3. Compares the upstream signed executable to `Data/Runtime/rufus.exe` using SHA256; only an updated executable is copied to `Data/Runtime`, with an atomic swap. This preserves settings and prevents upgrades from erasing runtime files.
4. Backs up `rufus.ini` to `Data/TraceGuard/Backups` before swapping to a new binary version.
5. Creates an `active-session.txt` crash journal. All application-relative settings are already inside `Data`; a crash cannot interrupt a settings relocation.
6. Runs Rufus using Windows `ShellExecuteEx`, forwarding command-line arguments and waiting for its process handle.
7. Creates a TraceGuard inventory of files **and nested empty directories** inside `Data/Runtime`. Unexpected reparse points are rejected.
8. Preserves prior session records if a previous launcher crashed, and never intentionally deletes user settings or run-created data.

The launcher does not sweep arbitrary AppData, registry, TEMP, ProgramData or system locations. Automatically moving newly discovered host files would risk taking ownership of unrelated data. See `docs/PORTABILITY-AUDIT.md` and `docs/LIMITATIONS.md`.

## Beginner-friendly GitHub Desktop setup

1. Make a **new, separate** GitHub repository, suggested name: `Rufus-PortableApps-Builder`. **Do not fork** `pbatard/rufus`.
2. Choose **Public** if anyone should see the builder source and its releases. Choose **Private** if only you and authorized collaborators should access the release files. GitHub private releases stay in the private repository.
3. Download and extract `Rufus_PortableApps_Builder_b1r1.zip`. Ensure hidden `.github` is included.
4. In GitHub Desktop, choose **File → New Repository**; use the new repository folder. Choose **Repository → Show in Explorer**, and copy all extracted files and directories (including `.github`) there.
5. In GitHub Desktop, enter **Summary**: `Initial Rufus PortableApps builder b1r1` and click **Commit to main**. Click **Publish repository** and choose the visibility already decided.
6. On GitHub, choose **Actions**. Enable workflows if GitHub asks.
7. Choose **Build Rufus PortableApps → Run workflow**. Leave the upstream version blank (automatic latest stable), choose `custom-nsis`, and check `publish_release` if you want the completed packages published.
8. Open the completed Actions run. If green, look under **Releases** in your NEW builder repository. Download the `RufusPortable_*.zip` or independent `*.paf.exe` installer.
9. ZIP: extract the `RufusPortable` directory into your PortableApps root; start `RufusPortable.exe` or use the PortableApps menu. Installer: run the `.paf.exe` and choose the location of your PortableApps platform.
10. For upgrades, **keep the existing `Data` folder**. Replace only program files, or use the same-name upgraded independent installer after closing Rufus. Back up `Data` before any downgrade.
11. **Rebuild Installer From Validated Release ZIP** takes an existing, publisher-verified source release tag and packages a new installer revision without downloading or compiling Rufus again.
12. **Check Rufus and Builder Compatibility (No Publishing)** reports newer stable releases and newer shared action tags without changing files or publishing.

### Workflows

| Workflow | Does | Publishes? |
| --- | --- | --- |
| `Build Rufus PortableApps` | Resolves official stable version, audits source, checks signature, compiles launcher, checks synthetic runtime, creates ZIP and shared installer | Optional, enabled by default |
| `Rebuild Installer From Validated Release ZIP` | Downloads and validates existing release ZIP/SHA256SUMS, builds a new installer with shared packager | Optional, enabled by default |
| `Check Rufus and Builder Compatibility (No Publishing)` | Read-only stable-release and dependency status report | Never |

No workflow runs automatically on a schedule. No manual source patch is required for compatible new upstream versions.

### Build options

The normal setting is `custom-nsis`. This produces an **independent community-built** installer using `vhick/Portable-Package-Builder@v1.0.0`. This is **not** an official PortableApps.com Installer and carries no third-party certification.

`official` is EXPERIMENTAL. Supply both the actual official PortableApps.com Installer tool HTTPS download URL and authentic vendor-published SHA-256. The shared packager decides if it can run. We will not silently fall back to the custom engine.

GitHub first-party Actions are pinned to verified 2026 versions: `actions/checkout@v7.0.1`, `actions/setup-python@v7.1.0`, and failure-only `actions/upload-artifact@v7.0.2`. The pinned Release Publisher is `vhick/portable-release-publisher@v1.1.1` with a dry-run before publication, three-release retention setting, and `prune=false` (no automatic release deletions).

### Safe future updates

- Release versions are selected numerically, not by publish date, and prereleases are excluded.
- Release assets are selected with strict version-aware portable x64 patterns; a changed but recognizable official filename is supported.
- Unique signed official GitHub Release assets are downloaded over HTTPS and checked for content size, ZIP-style asset SHA metadata if provided, PE architecture, Windows Authenticode status, the approved signer name, and version matching.
- Exact corresponding release tag source is downloaded for static portable-mode contract checks. Changed source layouts can pass if the same evidenced portable feature is retained.
- Source compilation is not required. No NuGet, Rust, Node or Python dependencies are installed for Rufus itself. The only compiler needed is MSVC C++ for the launcher; the workflow discovers an installed compatible VS toolchain on `windows-latest`.
- The completed package records official binary checksum, source commit, used shared action tags and package revision.
- Existing release tags are never silently overwritten. If the same stable version and revision already exist, a normal build skips work. If a new builder revision is necessary, change only `package_revision` in `config/builder.json`; the build workflow passes that value through to the shared packager and publisher.
- A changed Rufus portable contract, missing official asset/signature, invalid source, unavailable compiler or unsupported shared packager blocks publication and leaves existing releases untouched.

## Reproducibility / known-good

The kit contains `config/known-good.json` as an explicit **uninitialized** reference, not a falsely populated passing record. Every actual successful package embeds `Other/Source/build-manifest.json` describing version, official asset SHA, tagged source commit, verified Authenticode signer and selected builder integrations. Published GitHub Releases plus their `SHA256SUMS.txt` are the durable known-good assets. Do not modify or delete a previous release to make a new one seem successful.

Runtime data is intentionally **not** embedded in new packages or installers. An upgrade should preserve `Data/Runtime/rufus.ini`, `Data/TraceGuard/Backups`, recovered session journals and any newly created files and empty directories.

## Limitations and troubleshooting

Review `docs/PORTABILITY-AUDIT.md`, `docs/QUALITY-ASSURANCE.md`, and `docs/LIMITATIONS.md`. Most common failures:

- **No signed stable asset:** upstream renamed or removed a format; don't bypass signature, version or architecture checks.
- **No MSVC:** verify the Windows runner includes Visual Studio Build Tools and Windows SDK; the launcher uses system APIs, not Rufus source compilation.
- **Source contract changed:** inspect upstream's new settings implementation; adjust the precise adapter only after testing.
- **Installer fails:** keep the ZIP-only failure artifact from the Actions run for up to 3 days; fix the shared package interface or staged metadata, not the official Rufus binary.
- **Rufus settings do not persist:** check write permissions and `RufusPortable/Data/Runtime/rufus.ini`; do not move or delete `Data` while the app runs.
- **USB operation fails:** Rufus may require administrator elevation; that does not mean the wrapper should bypass UAC. Use the official Rufus log and documentation.
- **Release publication blocked:** inspect immutable release collision, publisher dry-run output, and job contents permission.

## References

- Rufus repository: https://github.com/pbatard/rufus
- Official releases: https://github.com/pbatard/rufus/releases
- Rufus portable FAQ: https://github.com/pbatard/rufus/wiki/FAQ
- Native INI sample: https://github.com/pbatard/rufus/blob/master/res/rufus.ini
- Universal packager pinned action: https://github.com/vhick/Portable-Package-Builder/blob/v1.0.0/action.yml
- Universal publisher pinned action: https://github.com/vhick/portable-release-publisher/blob/v1.1.1/action.yml
