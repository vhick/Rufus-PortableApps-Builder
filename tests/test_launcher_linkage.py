"""Static regression checks for the MSVC launcher link contract.

This is deliberately lightweight; GitHub Actions still compiles the real launcher
on Windows, and only that run can prove Windows link success.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LauncherLinkageTests(unittest.TestCase):
    def test_user32_import_library_for_messageboxw(self):
        source = (ROOT / 'launcher/RufusPortable.cpp').read_text(encoding='utf-8')
        self.assertIn('MessageBoxW(', source)
        # On MSVC, a pragma in the compilation unit injects /DEFAULTLIB:User32.lib.
        self.assertRegex(source, r'(?im)^\s*#pragma\s+comment\s*\(\s*lib\s*,\s*"User32\.lib"\s*\)')

    def test_windows_macro_is_declared_in_one_place(self):
        source = (ROOT / 'launcher/RufusPortable.cpp').read_text(encoding='utf-8')
        builder = (ROOT / 'scripts/build-launcher.ps1').read_text(encoding='utf-8')
        self.assertEqual(source.count('#define WIN32_LEAN_AND_MEAN'), 1)
        self.assertNotIn('/DWIN32_LEAN_AND_MEAN', builder)

    def test_link_step_does_not_ignore_failed_compilation(self):
        builder = (ROOT / 'scripts/build-launcher.ps1').read_text(encoding='utf-8')
        self.assertIn('cl.exe /nologo', builder)
        self.assertIn('/link /SUBSYSTEM:WINDOWS', builder)
        self.assertIn('|| exit /b 15', builder)
        self.assertIn('if ($LASTEXITCODE -ne 0)', builder)


if __name__ == '__main__':
    unittest.main()
