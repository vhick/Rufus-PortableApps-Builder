"""Regress the Rufus missing *.html packaging failure from Actions run 45131252513."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'ensure-official-help.py'
spec = importlib.util.spec_from_file_location('rufus_html_helper', SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class OfficialHTMLRequired(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'RufusPortable'
        (self.root / 'App' / 'AppInfo').mkdir(parents=True)
        (self.root / 'App' / 'AppInfo' / 'appinfo.ini').write_text('[Format]\nType=PortableApps.comFormat\n')
        (self.root / 'RufusPortable.exe').write_bytes(b'MZ' + b'\0' * 50)
        (self.root / 'Data').mkdir()
        (self.root / 'Data' / 'private.txt').write_text('KEEP PRIVATE')

    def tearDown(self):
        self.tmp.cleanup()

    def test_help_is_root_html_and_preserves_user_data(self):
        before = (self.root / 'Data/private.txt').read_bytes()
        self.assertTrue(helper.ensure_help(self.root))
        html = self.root / 'help.html'
        self.assertTrue(html.is_file())
        self.assertIn('RufusPortable.exe', html.read_text())
        self.assertEqual(before, (self.root / 'Data/private.txt').read_bytes())
        self.assertEqual([p.name for p in self.root.glob('*.html')], ['help.html'])

    def test_idempotent_does_not_overwrite_existing_help(self):
        self.assertTrue(helper.ensure_help(self.root))
        content = (self.root / 'help.html').read_bytes()
        self.assertFalse(helper.ensure_help(self.root))
        self.assertEqual(content, (self.root / 'help.html').read_bytes())

    def test_preserves_preexisting_valid_help(self):
        custom = b'<html><body>My documented help page</body></html>'
        (self.root / 'help.html').write_bytes(custom)
        self.assertFalse(helper.ensure_help(self.root))
        self.assertEqual(custom, (self.root / 'help.html').read_bytes())

    def test_rejects_empty_or_invalid_help(self):
        (self.root / 'help.html').write_bytes(b'')
        with self.assertRaises(ValueError):
            helper.ensure_help(self.root)

    def test_rejects_invalid_package_without_writing(self):
        (self.root / 'App/AppInfo/appinfo.ini').unlink()
        with self.assertRaises(ValueError):
            helper.ensure_help(self.root)
        self.assertFalse((self.root / 'help.html').exists())

    def test_main_and_repack_only_change_official_branch(self):
        for rel in ['.github/workflows/build-rufus-portableapps.yml', '.github/workflows/packaging-only.yml']:
            wf = (ROOT / rel).read_text(encoding='utf-8')
            self.assertIn('python scripts/ensure-official-help.py', wf)
            self.assertIn("inputs.packaging_engine == 'official'", wf)
            self.assertLess(wf.index('scripts/ensure-official-help.py'), wf.index('uses: vhick/Portable-Package-Builder@'))
            self.assertNotIn('official_tool_url', wf)
            self.assertNotIn('official_tool_sha256', wf)
        main = (ROOT / '.github/workflows/build-rufus-portableapps.yml').read_text()
        self.assertLess(main.index('scripts/ensure-official-help.py'), main.index('scripts/finalize.ps1'))
        conf = json.loads((ROOT / 'config/builder.json').read_text())
        self.assertEqual(conf['package_revision'], 'b1r5')

if __name__ == '__main__':
    unittest.main()
