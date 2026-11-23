# Rufus b1r5: official Installer 3.9.24 root HTML source prerequisite

## Confirmed failure
GitHub Actions build run `45131252513` compiled the Rufus portable launcher and independent ZIP, then failed in the genuine official NSIS source on line 1796:

```text
File: "..\..\*.html" -> no files found.
Error in script PortableApps.comInstaller.nsi on line 1796
```

The failed `RufusPortable_4.16_b1r4.zip` contains the portable root executable, Rufus binary, AppInfo, and source, but no root `*.html` file. The upstream NSIS script requires that file without `/nonfatal`.

## Fix
For **official only**, after staging and metadata normalization and before generating the independent ZIP, run `scripts/ensure-official-help.py`. It adds a **genuine user-help file** from `assets/help.html` containing Rufus usage, safety warnings, portability instructions, and upstream links. For the installer-only workflow, do the same after validating and extracting the trusted ZIP.

It is intentionally not a blank compile-only placeholder. The script preserves any existing meaningful `help.html` and never touches binaries, launcher, other source, or user `Data`.

The `custom-nsis` branch remains unchanged. The pinned shared source compiler stays at `78da3c258bd7da63740d94b4b40902dde82f7df3` and uses the bundled PortableApps.com Installer 3.9.24 NSIS source. No installer executable download or interactive wizard.

## Test
1. Overlay this update on your existing Rufus builder repository and push.
2. GitHub Actions → **Build Rufus PortableApps** → **Run workflow**.
3. Choose `upstream_version` blank, `packaging_engine=official`, `publish_release=false`.
4. Look for `OFFICIAL_HTML_ADDED:` in the log before the Zip and `Build selected PortableApps installer` steps.
5. On success, download the artifact `rufus-4.16-b1r5-official-test` (or the dynamically selected latest version), and test clean install + upgrade over a backed-up `Data` folder.

The previous zipped artifact was a **diagnostic**, not a successful installer. Do not publish this new revision until the real Windows build and installation/upgrade checks pass.

## Verification limit
Regression tests confirm that a root `help.html` is added safely before compiler invocation and the resulting staged folder satisfies the missing NSIS file glob. Linux validation cannot execute the Windows-only NSIS compiler. Additional compilation or behavior errors may still be discovered in the actual Actions run.
