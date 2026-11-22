import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from resolve import select_release, select_asset, inspect_pe
from audit import audit_source


def release(version, name='', prerelease=False, asset=''):
    return {'tag_name': 'v' + version, 'name': name or 'Rufus ' + version,
            'prerelease': prerelease, 'draft': False, 'published_at': '2026-01-01T00:00:00Z',
            'assets': [{'name': asset or f'rufus-{version}p.exe',
                        'browser_download_url': f'https://github.com/pbatard/rufus/releases/download/v{version}/{asset or "rufus-"+version+"p.exe"}',
                        'size': 2000000}]}


class ResolverTests(unittest.TestCase):
    def test_numeric_sort_over_published_order(self):
        a = [release('4.9'), release('4.16'), release('4.15')]
        self.assertEqual(select_release(a)['tag_name'], 'v4.16')

    def test_prerelease_excluded(self):
        a = [release('4.17', 'Rufus 4.17 BETA'), release('4.16')]
        self.assertEqual(select_release(a)['tag_name'], 'v4.16')

    def test_renamed_portable_asset(self):
        a = release('5.1', asset='rufus_5.1_x64_portable.exe')
        self.assertEqual(select_asset(a)['name'], 'rufus_5.1_x64_portable.exe')

    def test_binary_ambiguity_is_fatal(self):
        a = release('5.1')
        a['assets'].append(dict(a['assets'][0]))
        with self.assertRaisesRegex(RuntimeError, 'precisely one'):
            select_asset(a)

    def test_untrusted_url_is_fatal(self):
        a = release('5.1')
        a['assets'][0]['browser_download_url'] = 'https://example.com/rufus.exe'
        with self.assertRaisesRegex(RuntimeError, 'unexpected origin'):
            select_asset(a)

    def test_no_compatible_release(self):
        with self.assertRaises(RuntimeError):
            select_release([release('4.17', 'Rufus 4.17 BETA')])

    def test_source_layout_can_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.git').mkdir()
            (root / 'new/layout').mkdir(parents=True)
            (root / 'new/layout/rufus.ini').write_text('rufus.ini portable mode instead of Registry')
            (root / 'new/layout/implementation.cpp').write_text('const char* x="rufus.ini"; int ini_flags=0;')
            result = audit_source(root, '5.1', 'a' * 40)
            self.assertEqual(result['source_check'], 'PASS')

    def test_source_breaking_change_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.git').mkdir()
            (root / 'rufus.ini').write_text('rufus.ini portable mode instead of Registry')
            (root / 'app.cpp').write_text('NewRegistryOnlySettings();')
            with self.assertRaisesRegex(RuntimeError, 'no longer demonstrates'):
                audit_source(root, '9.0', 'a' * 40)


if __name__ == '__main__':
    unittest.main()
