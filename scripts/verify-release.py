#!/usr/bin/env python3
"""For packaging-only: validate a release ZIP against its publisher SHA256SUMS.txt."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
from package import validate_zip

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip', required=True)
    parser.add_argument('--sums', required=True)
    args = parser.parse_args()
    z = Path(args.zip)
    sums = Path(args.sums).read_text(encoding='utf-8-sig')
    lines = {}
    for line in sums.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2 and len(parts[0]) == 64:
            lines[parts[1].lstrip(' *')] = parts[0].lower()
    expected = lines.get(z.name)
    if not expected:
        raise RuntimeError('Release SHA256SUMS.txt does not contain selected ZIP filename')
    found = hashlib.sha256(z.read_bytes()).hexdigest()
    if expected != found:
        raise RuntimeError('Downloaded release ZIP fails publisher checksum')
    manifest = validate_zip(z)
    print('Verified archived portable release:', json.dumps(manifest, indent=2))
    if 'GITHUB_OUTPUT' in __import__('os').environ:
        with open(__import__('os').environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
            f.write('version=' + manifest['upstream_version'] + '\n')

if __name__ == '__main__':
    try: main()
    except Exception as e:
        print('PACKAGING-ONLY PROVENANCE CHECK FAILED:', e, file=sys.stderr)
        sys.exit(1)
