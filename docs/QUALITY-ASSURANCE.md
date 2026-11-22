# Quality assurance and future-release policy

## Automated (test definitions included; run results are not fabricated)

1. `python -m unittest discover -s tests -p 'test_*.py' -v` tests numeric version sorting, prerelease rejection, renamed portable asset matching, ambiguous assets fail closed, untrusted origins rejected, moved source tree accepted, removed INI semantics rejected.
2. GitHub Actions runs the source-tag `audit.py` and verifies a signed upstream x64 PE, signer name, file version and SHA256.
3. Actions discovers MSVC through `vswhere`; compiles the real C++ launcher, whose output is required to be a Windows PE.
4. `tests/runtime-fixture.ps1` uses a **fake executable**, not Rufus, to test first launch, direct INI writes inside Data, file and nested empty-directory preservation, binary updates and INI backup, stale crash journal recovery, filesystem relocation.
5. `scripts/package.py` verifies archive traversal safety, unique names, PortableApps metadata, exact signed binary SHA, genuine launcher PE and empty Data directory. ZIP generation is independent of installer generation.
6. The shared packager checks installer PE and 7-Zip archive integrity; builder independently hashes the returned installer output.
7. The publisher first runs dry-run and then actual publication, with no overwrite of existing tags and prune disabled.

## Manual Windows acceptance (required before claiming Rufus is fully usable)

- Run ZIP `RufusPortable.exe` from a non-admin Windows account and observe that Rufus asks for the privileges it requires.
- Close Rufus; inspect `Data/Runtime/rufus.ini` and `Data/TraceGuard/runtime-inventory.tsv`.
- Change Rufus language or a harmless persistent preference, close and reopen from a different directory/drive letter; verify persistence.
- Create an empty and a nested empty folder manually in `Data/Runtime`, then run and exit, verify both appear in inventory.
- Test backup of the complete `Data` tree and recovery of a pre-upgrade settings snapshot.
- Install a newer package over the same folder while Rufus is closed, verify `Data` intact and obsolete program files handled by the pinned shared packager.
- If a downgrade is required, restore a **backed-up** `Data` directory. Future upstream migrations may not support downgrades.
- Only for a spare, disposable drive with the correct device selected: test actual Rufus writing separately from CI and verify no unrelated drive changes.
- Inspect Windows host traces and system changes with appropriate approved tools, not a destructive cleanup script.

## Compatibility and failure guarantees

- **Adapt automatically:** numeric stable versions, official portable asset filename variations recognized by strict metadata, compatible source code moves, runner MSVC path changes, zip version metadata, compiler version changes that compile and pass fixture tests.
- **Stop for review:** removed portable INI behavior, non-x64 release, changed signature publisher, new Windows runtime requirements, missing official binary, changed shared action interface, missing compiler, unrecognized new persistent host storage.
- **Never silently repair:** disabling signature checks, patching unrelated upstream source, overwriting old published releases, deleting unknown host data, skipping mandatory packager test, changing shared action pin.

Runtime smoke tests test the **launcher with a fake application**. They do not prove the entire Rufus application works with every possible USB device and Windows installation. Keep this distinction in run reports.

## b1r2 regression: Windows CRLF `appinfo.ini`

Previously the CI preflight failed because a line-anchored version regex assumed Unix LF. Regression tests now explicitly create Windows CRLF INI with a UTF-8 BOM and verify independent ZIP checksums and integrity, plus rejection of invalid package versions and versions in the wrong INI section. The offline tests can run on Linux, but Windows GitHub Actions must independently confirm the fix.

## b1r3 MSVC linker regression check

- Run `python -m unittest discover -s tests -p 'test_*.py' -v`. `test_launcher_linkage.py` verifies the `MessageBoxW` import library declaration, avoids duplicate `WIN32_LEAN_AND_MEAN`, and confirms link failures remain fatal.
- Re-run the manual `Build Rufus PortableApps` GitHub Actions workflow. The first real Windows launcher compilation and synthetic runtime test are still required. Do not mark them successful based solely on offline tests.
- Run `121889371100` proves preflight, stable tag auditing and official asset download but **not** launcher linking, fixture, ZIP packaging or installer creation.
