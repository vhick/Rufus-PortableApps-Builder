# Rufus PortableApps b1r4 — genuine official installer source test

## Scope

This update **does not change Rufus upstream binaries, the C++ portable launcher,
TraceGuard, native `rufus.ini`, runtime Data handling, packaging ZIP logic, or
Release Publisher**. It changes the shared installer action from the old
`v1.0.0` download-dependent engine to the r4 source-based compiler, pinned to
exact Git commit `78da3c258bd7da63740d94b4b40902dde82f7df3`.

The shared r4 GitHub smoke test succeeded on November 23, 2026. That smoke test
used a synthetic package, **not Rufus**. This b1r4 application-specific test must
run before treating the integration as stable or updating your universal prompt.

The Rufus-specific adapter also converts a display label such as `4.16 (b1r4)`
to `4.16 b1r4` for the official compiler. `PackageVersion`, executable,
portable launcher and settings are unchanged. This is necessary because the
reviewed r4 metadata generator rejects parentheses in `DisplayVersion`.

The official-source builder is original PortableApps.com Installer version
3.9.24 with its own NSIS compiler already inside that shared action commit.
**No SourceForge mirror request, download of PortableApps.comInstaller*.paf.exe,
or graphical wizard** is used when generating the Rufus installer.

## How to test with GitHub Actions

1. Extract this **overlay patch** into an existing clone of
   `vhick/Rufus-PortableApps-Builder`, allowing matching paths to be replaced.
   Do not delete `.git`, the existing `launcher`, or any existing `scripts`.
2. Use GitHub Desktop to review the changed files, commit the patch, and push.
3. Open GitHub → Rufus-PortableApps-Builder → Actions → **Build Rufus PortableApps**.
4. Click **Run workflow**. Choose:
   - Branch: `main`
   - Rufus version: **blank** for newest supported stable
   - Packaging engine: **`official`**
   - Publish validated ZIP + installer: **unchecked**
5. Let the run finish. The job must pass the Rufus binary signature check,
   source portability audit, launcher build, synthetic runtime fixture, ZIP
   verification, official-source NSIS compilation and installer checksum check.
6. In the completed Actions run, scroll to **Artifacts**. Download the artifact
   named `rufus-<version>-b1r4-official-test`. It includes one ZIP, the genuine
   vendor-source-built `.paf.exe`, its `.sha256`, and a provenance JSON file.
7. Inspect the official installer on Windows. First install to a fresh folder,
   launch `RufusPortable.exe`, and verify that configuration persists under
   `RufusPortable/Data/Runtime`. **Do not perform destructive USB operations as
   part of this acceptance test.**
8. For upgrade testing, create meaningful test settings and a test sentinel file
   inside `Data`, close Rufus completely, install over the existing folder, and
   verify settings, Data content, and the sentinel remain intact. Use a backed-up
   test folder, not a production USB installation.
9. Confirm that the `.paf.exe` filename/provenance identifies `official`, and
   no `PortableApps.comInstaller*.paf.exe` was downloaded in the build log.

When a public GitHub Release is desired *after acceptance*, select
`publish_release: true` in a new run. The previous and new releases are immutable;
never overwrite a published release tag. Keep `custom-nsis` available as an
independent fallback.

## Installer-only repackage

`Rebuild Installer From Validated Release ZIP` now has the same two engine choices
and no vendor tool URL/hash fields. It still requires a previous **published**,
checksummed Rufus builder ZIP as the input. It does **not** accept a temporary
GitHub Actions artifact ZIP, so it is not needed for the first b1r4 test.

## Limitations

- Static patch checks are not a substitute for actual Windows Rufus installation
  and upgrade testing.
- This change does not mean PortableApps.com officially approved the resulting
  community package. The output uses the upstream installer source template.
- The official compiler version remains **3.9.24** until its vendored source and
  hashes are explicitly reviewed and the shared builder is upgraded.
- Published Rufus packages contain an executable that may require admin rights
  and perform destructive disk operations when the user deliberately requests it.
