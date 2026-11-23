#!/usr/bin/env python3
"""Ensure the genuine PortableApps installer source has a useful root HTML file.

The vendor NSIS source (3.9.24, line 1796) has a fatal root HTML glob.
This step only runs for the official packaging engine. It never changes the
upstream NSIS template, application executable, launcher, AppInfo or Data.
"""
from pathlib import Path
import argparse
import sys


def ensure_help(root: Path) -> bool:
    root = Path(root)
    appinfo = root / 'App' / 'AppInfo' / 'appinfo.ini'
    launcher = root / 'RufusPortable.exe'
    if not root.is_dir() or not appinfo.is_file() or not launcher.is_file():
        raise ValueError(f'Invalid staged RufusPortable package at {root}')
    help_file = root / 'help.html'
    if help_file.is_symlink():
        raise ValueError('Refusing to follow an unexpected help.html symlink')
    if help_file.exists():
        if not help_file.is_file() or help_file.stat().st_size < 20:
            raise ValueError('Existing help.html is missing meaningful content')
        print(f'OFFICIAL_HTML_OK: Existing root help.html retained: {help_file}')
        return False
    template = Path(__file__).resolve().parents[1] / 'assets' / 'help.html'
    content = template.read_bytes()
    if not content.startswith(b'<!DOCTYPE html>') or b'RufusPortable.exe' not in content:
        raise ValueError('Bundled official help template was modified unexpectedly')
    # Exclusive creation avoids overwriting a preexisting user's help file.
    with help_file.open('xb') as f:
        f.write(content)
    print(f'OFFICIAL_HTML_ADDED: {help_file} ({len(content)} bytes)')
    return True


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    args = p.parse_args()
    try:
        ensure_help(args.root)
    except (ValueError, OSError) as e:
        print(f'OFFICIAL_HTML_INVALID: {e}', file=sys.stderr)
        sys.exit(2)
