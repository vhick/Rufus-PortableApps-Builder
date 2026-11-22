#!/usr/bin/env python3
"""Independent checked PortableApps ZIP creation and release ZIP verification."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import sys
import zipfile

REQUIRED = (
    'RufusPortable/RufusPortable.exe',
    'RufusPortable/App/AppInfo/appinfo.ini',
    'RufusPortable/App/AppInfo/appicon.ico',
    'RufusPortable/App/AppInfo/appicon_16.png',
    'RufusPortable/App/AppInfo/appicon_32.png',
    'RufusPortable/App/AppInfo/Launcher/RufusPortable.ini',
    'RufusPortable/App/Rufus/rufus.exe',
    'RufusPortable/App/Rufus/rufus.sha256',
    'RufusPortable/Other/Source/UPSTREAM-LICENSE.txt',
    'RufusPortable/Other/Source/build-manifest.json',
)


def check_pe(blob, machine=None):
    if len(blob) < 2048 or blob[:2] != b'MZ':
        raise ValueError('Not a valid PE executable (DOS header missing)')
    pointer = struct.unpack_from('<I', blob, 0x3c)[0]
    if pointer + 26 > len(blob) or blob[pointer:pointer + 4] != b'PE\x00\x00':
        raise ValueError('Windows PE header missing')
    if machine and struct.unpack_from('<H', blob, pointer + 4)[0] != machine:
        raise ValueError('Incorrect executable architecture')


def validate_info(info):
    if '[Details]' not in info or 'AppID=RufusPortable' not in info or 'Start=RufusPortable.exe' not in info:
        raise ValueError('PortableApps metadata missing expected launcher or AppID')
    if not re.search(r'(?m)^PackageVersion=\d+(?:\.\d+){3}$', info):
        raise ValueError('Missing 4-part PortableApps version')


def validate_zip(path):
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise ValueError('CRC error in ZIP entry: ' + bad)
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('ZIP contains duplicate filenames')
        for n in names:
            p = PurePosixPath(n)
            if p.is_absolute() or '..' in p.parts or '\\' in n or not n.startswith('RufusPortable/'):
                raise ValueError('ZIP traversal or unexpected root: ' + n)
            # File mode bit 0170000, symbolic link type 0120000.
            zi = z.getinfo(n)
            if (zi.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('ZIP symlink not allowed: ' + n)
        for name in REQUIRED:
            if name not in names:
                raise ValueError('ZIP is missing ' + name)
        if not any(n == 'RufusPortable/Data/' for n in names):
            raise ValueError('Missing empty persistent Data directory')
        if any(n.startswith('RufusPortable/Data/') and not n.endswith('/') for n in names):
            raise ValueError('Distributed archive must not contain user-owned Data')
        check_pe(z.read('RufusPortable/RufusPortable.exe'), 0x8664)
        check_pe(z.read('RufusPortable/App/Rufus/rufus.exe'), 0x8664)
        validate_info(z.read('RufusPortable/App/AppInfo/appinfo.ini').decode('utf-8-sig'))
        manifest = json.loads(z.read('RufusPortable/Other/Source/build-manifest.json'))
        vendor_sha = hashlib.sha256(z.read('RufusPortable/App/Rufus/rufus.exe')).hexdigest()
        if manifest['asset_sha256'] != vendor_sha:
            raise ValueError('Upstream executable differs from embedded provenance checksum')
        if z.read('RufusPortable/App/Rufus/rufus.sha256').decode('ascii').strip().lower() != vendor_sha:
            raise ValueError('Portable launcher payload hash does not match upstream executable')
        if 'launcher_sha256' in manifest and manifest['launcher_sha256'] != hashlib.sha256(z.read('RufusPortable/RufusPortable.exe')).hexdigest():
            raise ValueError('Compiled launcher differs from recorded provenance SHA256')
    return manifest


def create_zip(folder, target):
    folder, target = Path(folder), Path(target)
    if folder.name != 'RufusPortable':
        raise ValueError('Expected an assembled RufusPortable directory')
    if target.exists():
        raise ValueError('Refusing to overwrite completed package ' + str(target))
    files = sorted(folder.rglob('*'))
    target.parent.mkdir(parents=True, exist_ok=True)
    # Fixed archive timestamps ensure archive determinism for identical inputs.
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as z:
        for p in files:
            if p.is_symlink():
                raise ValueError('Unsafe symbolic link in staging: ' + str(p))
            is_dir = p.is_dir()
            rel = p.relative_to(folder.parent).as_posix() + ('/' if is_dir else '')
            zi = zipfile.ZipInfo(rel, date_time=(2020, 1, 1, 0, 0, 0))
            zi.create_system = 0
            zi.external_attr = 0x10 if is_dir else 0x20
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, b'' if is_dir else p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    manifest = validate_zip(target)
    h = hashlib.sha256(target.read_bytes()).hexdigest()
    print(f'VALIDATED PortableApps ZIP: {target} | SHA256 {h} | Rufus {manifest["upstream_version"]}')
    return h


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='command', required=True)
    c = subs.add_parser('create'); c.add_argument('--stage', default='work/stage/RufusPortable'); c.add_argument('--output', required=True)
    v = subs.add_parser('verify'); v.add_argument('--zip', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'create':
            create_zip(args.stage, args.output)
        else:
            print('VERIFIED ZIP:', args.zip, json.dumps(validate_zip(args.zip), indent=2))
    except Exception as exc:
        print('PORTABLE ZIP CHECK FAILED:', exc, file=sys.stderr)
        sys.exit(1)
