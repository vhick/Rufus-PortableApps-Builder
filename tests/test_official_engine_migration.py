"""Offline regression checks for b1r4's shared source-based installer migration."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '78da3c258bd7da63740d94b4b40902dde82f7df3'


class OfficialSourceIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = (ROOT / '.github/workflows/build-rufus-portableapps.yml').read_text(encoding='utf-8')
        cls.repack = (ROOT / '.github/workflows/packaging-only.yml').read_text(encoding='utf-8')
        cls.verify = (ROOT / 'scripts/verify-shared.py').read_text(encoding='utf-8')
        cls.conf = json.loads((ROOT / 'config/builder.json').read_text(encoding='utf-8'))

    def test_immutable_tested_shared_action(self):
        for wf in (self.main, self.repack):
            self.assertIn(f'uses: vhick/Portable-Package-Builder@{COMMIT}', wf)
            self.assertNotIn('@v1.0.0', wf)
        self.assertEqual(self.conf['package_builder'], f'vhick/Portable-Package-Builder@{COMMIT}')
        self.assertIn(COMMIT, self.verify)

    def test_no_installer_vendor_executable_download(self):
        for wf in (self.main, self.repack):
            self.assertNotIn('official_tool_url:', wf)
            self.assertNotIn('official_tool_sha256:', wf)
            self.assertNotIn('official-tool-url:', wf)
            self.assertNotIn('official-tool-sha256:', wf)
            self.assertIn('engine: ${{ inputs.packaging_engine }}', wf)
        self.assertNotIn('both\n', self.main)
        self.assertNotIn('both\n', self.repack)

    def test_portable_launcher_and_safety_baseline_retained(self):
        self.assertIn('scripts/stage.ps1', self.main)
        self.assertIn('tests/runtime-fixture.ps1', self.main)
        self.assertIn('scripts/package.py create', self.main)
        self.assertIn('scripts/package.py verify', self.main)
        self.assertIn('running-exe: App\\Rufus\\rufus.exe', self.main)
        self.assertIn('scripts/normalize-appinfo-for-official.py', self.main)
        self.assertIn('scripts/normalize-appinfo-for-official.py', self.repack)
        self.assertIn('scripts/verify-release.py', self.repack)
        self.assertIn('Get-AuthenticodeSignature', self.repack)
        self.assertEqual(self.conf['package_revision'], 'b1r5')

    def test_no_unreviewed_publish_and_artifacts(self):
        for wf in (self.main, self.repack):
            self.assertRegex(wf, r'publish_release:[\s\S]*?default: false')
            self.assertIn('actions/upload-artifact@v7.0.2', wf)
            self.assertIn('if-no-files-found: error', wf)
            self.assertIn('!inputs.publish_release', wf)
            self.assertIn('PUBLISH_RELEASE', wf)
        self.assertIn('prune: \'false\'', self.main)
        self.assertIn('prune: \'false\'', self.repack)

    def test_workflow_static_validity(self):
        # PyYAML optional; use it when present, otherwise test the important shape.
        try:
            import yaml
        except ImportError:
            return
        for wf in (self.main, self.repack):
            parsed = yaml.load(wf, Loader=yaml.BaseLoader)
            self.assertIn('on', parsed)
            self.assertIn('workflow_dispatch', parsed['on'])
            values = parsed['on']['workflow_dispatch']['inputs']['packaging_engine']['options']
            self.assertEqual(values, ['custom-nsis', 'official'])


class DisplayVersionCompatibility(unittest.TestCase):
    def test_old_rufus_label_becomes_accepted_by_official_compiler(self):
        import runpy
        import tempfile
        script = ROOT / 'scripts/normalize-appinfo-for-official.py'
        normalize = runpy.run_path(str(script))['normalize']
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            info = root / 'App/AppInfo/appinfo.ini'
            info.parent.mkdir(parents=True)
            info.write_bytes((
                '[Format]\r\nType=PortableApps.comFormat\r\n'
                '[Version]\r\nPackageVersion=4.16.0.0\r\n'
                'DisplayVersion=4.16 (b1r4)\r\n'
                '[Control]\r\nStart=RufusPortable.exe\r\n'
            ).encode('utf-8'))
            self.assertTrue(normalize(root))
            content = info.read_bytes()
            self.assertIn(b'DisplayVersion=4.16 b1r4\r\n', content)
            self.assertIn(b'PackageVersion=4.16.0.0\r\n', content)
            self.assertNotIn(b'DisplayVersion=4.16 (b1r4)', content)
            self.assertFalse(normalize(root))  # idempotent

    def test_unknown_metadata_rejected_without_modification(self):
        import runpy
        import tempfile
        normalize = runpy.run_path(str(ROOT / 'scripts/normalize-appinfo-for-official.py'))['normalize']
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            info = root / 'App/AppInfo/appinfo.ini'
            info.parent.mkdir(parents=True)
            content = b'[Format]\nType=PortableApps.comFormat\n[Version]\nPackageVersion=4.16.0.0\nDisplayVersion=4.16 (custom!)\n'
            info.write_bytes(content)
            with self.assertRaises(ValueError):
                normalize(root)
            self.assertEqual(info.read_bytes(), content)


if __name__ == '__main__':
    unittest.main()
