#!/usr/bin/env python3
"""Make Rufus DisplayVersion compatible with pinned official 3.9.24 source.

Only for the `official` engine. Rufus's original staged value is, for example,
`4.16 (b1r4)`. The reviewed upstream r4 generator accepts the same version
without parentheses (`4.16 b1r4`). Never change PackageVersion, data, binary,
launcher, checksum, or other app metadata. Explicitly stop on unknown format.
"""
import argparse
import configparser
from pathlib import Path
import re
import sys

SAFE = re.compile(r'[0-9A-Za-z ._+\-]+\Z')
LEGACY = re.compile(r'(?P<version>[0-9]+(?:\.[0-9]+){1,3})\s+\((?P<revision>[A-Za-z0-9_-]+)\)\Z')


def normalize(root):
    path = Path(root) / 'App' / 'AppInfo' / 'appinfo.ini'
    if not path.is_file():
        raise ValueError(f'Missing official compiler input: {path}')
    original_bytes = path.read_bytes()
    has_bom = original_bytes.startswith(b'\xef\xbb\xbf')
    original = original_bytes.decode('utf-8-sig')
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.read_string(original)
    if parser.get('Format', 'Type', fallback='') != 'PortableApps.comFormat':
        raise ValueError('Not a PortableApps.com Format package')
    display = parser.get('Version', 'DisplayVersion', fallback='').strip()
    package = parser.get('Version', 'PackageVersion', fallback='').strip()
    if not re.fullmatch(r'\d+(?:\.\d+){3}', package):
        raise ValueError('Invalid four-number PackageVersion')
    if SAFE.fullmatch(display):
        print('Official source DisplayVersion already compatible:', display)
        return False
    match = LEGACY.fullmatch(display)
    if not match:
        raise ValueError(f'Official source rejects unsupported DisplayVersion: {display!r}')
    normalized = f'{match.group("version")} {match.group("revision")}'
    if not SAFE.fullmatch(normalized):
        raise ValueError('Unexpected normalized DisplayVersion')
    # Replace exactly the one [Version].DisplayVersion assignment; fail on
    # ambiguous or duplicate rows. Keep all original whitespace and newlines.
    section = None
    found = 0
    lines = original.splitlines(keepends=True)
    for index, line in enumerate(lines):
        match_section = re.match(r'^\s*\[([^\]\r\n]+)\]\s*(?:\r?\n)?$', line)
        if match_section:
            section = match_section.group(1).strip().lower()
        if section != 'version':
            continue
        m = re.match(r'^(?P<prefix>\s*DisplayVersion\s*=\s*)(?P<value>[^\r\n]*)(?P<eol>\r?\n|)$', line, flags=re.I)
        if m:
            found += 1
            if m.group('value').strip() != display:
                raise ValueError('DisplayVersion line disagrees with parser')
            lines[index] = m.group('prefix') + normalized + m.group('eol')
    if found != 1:
        raise ValueError(f'Expected exactly one Version.DisplayVersion row, found {found}')
    new_text = ''.join(lines)
    new_bytes = (b'\xef\xbb\xbf' if has_bom else b'') + new_text.encode('utf-8')
    # Same package except for the display label; do not change primary version.
    path.write_bytes(new_bytes)
    print('OFFICIAL_SOURCE_DISPLAY_VERSION_NORMALIZED:', display, '->', normalized)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    try:
        normalize(args.root)
    except Exception as e:
        print('OFFICIAL_METADATA_UNSUPPORTED:', e, file=sys.stderr)
        sys.exit(2)
