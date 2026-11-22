import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from package import create_zip, validate_zip


def tiny_x64_pe():
    image = bytearray(4096)
    image[:2] = b'MZ'
    struct.pack_into('<I', image, 0x3c, 0x80)
    image[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<H', image, 0x84, 0x8664)
    return bytes(image)


class PackageTests(unittest.TestCase):
    def setup_fixture(self, directory):
        stage = Path(directory) / 'RufusPortable'
        for p in ('App/AppInfo/Launcher', 'App/Rufus', 'Data', 'Other/Source'):
            (stage / p).mkdir(parents=True)
        (stage / 'RufusPortable.exe').write_bytes(tiny_x64_pe())
        (stage / 'App/Rufus/rufus.exe').write_bytes(tiny_x64_pe())
        (stage / 'App/Rufus/rufus.sha256').write_text(hashlib.sha256(tiny_x64_pe()).hexdigest())
        (stage / 'App/AppInfo/appinfo.ini').write_text('''[Format]\nType=PortableApps.comFormat\n[Details]\nAppID=RufusPortable\nName=Rufus Portable\n[Version]\nPackageVersion=4.16.0.0\n[Control]\nStart=RufusPortable.exe\n''')
        for p in ('appicon.ico', 'appicon_16.png', 'appicon_32.png'):
            (stage / 'App/AppInfo' / p).write_bytes(b'ICON')
        (stage / 'App/AppInfo/Launcher/RufusPortable.ini').write_text('LauncherType=Native')
        (stage / 'Other/Source/UPSTREAM-LICENSE.txt').write_text('Rufus license GPLv3')
        (stage / 'Other/Source/build-manifest.json').write_text(json.dumps({
            'upstream_version': '4.16',
            'asset_sha256': hashlib.sha256(tiny_x64_pe()).hexdigest()
        }))
        return stage

    def test_independent_zip_and_empty_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = self.setup_fixture(tmp)
            target = Path(tmp) / 'out.zip'
            create_zip(stage, target)
            self.assertEqual(validate_zip(target)['upstream_version'], '4.16')

    def test_reject_user_data_inside_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = self.setup_fixture(tmp)
            (stage / 'Data/my-secret.txt').write_text('do not package user data')
            with self.assertRaisesRegex(ValueError, 'user-owned Data'):
                create_zip(stage, Path(tmp) / 'out.zip')

    def test_reject_modified_upstream_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = self.setup_fixture(tmp)
            (stage / 'App/Rufus/rufus.exe').write_bytes(tiny_x64_pe() + b'changed')
            with self.assertRaisesRegex(ValueError, 'provenance checksum'):
                create_zip(stage, Path(tmp) / 'out.zip')

    def test_zip_rejects_path_escape(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'malicious.zip'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('../steal.txt', 'bad')
            with self.assertRaisesRegex(ValueError, 'traversal'):
                validate_zip(p)


if __name__ == '__main__':
    unittest.main()
