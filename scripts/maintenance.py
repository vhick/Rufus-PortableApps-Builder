#!/usr/bin/env python3
"""Read-only Rufus/builder compatibility report; never upgrades automatically."""
import json
import os
from pathlib import Path
from resolve import resolve, get_json


def main():
    meta = resolve('', Path('work/maintenance-release.json'))
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    releases = get_json('https://api.github.com/repos/' + repo + '/releases?per_page=100') if repo else []
    managed = [r for r in releases if r.get('tag_name', '').startswith('portable-v') and not r.get('draft')]
    latest = managed[0]['tag_name'] if managed else '(no known-good publication yet)'
    cfg = json.loads(Path('config/builder.json').read_text(encoding='utf-8'))
    expected_tag = 'portable-v' + meta['version'] + '-' + cfg['package_revision']
    newer = expected_tag not in {r['tag_name'] for r in managed}
    try:
        tags = get_json('https://api.github.com/repos/vhick/Portable-Package-Builder/tags?per_page=10')
        tagged = tags[0]['name'] if tags else 'none'
    except Exception as ex:
        tagged = 'unavailable: ' + str(ex)
    lines = [
        '# Rufus read-only maintenance report', '',
        f'- Latest official stable Rufus: `{meta["tag"]}`',
        f'- Latest existing builder release: `{latest}`',
        f'- Need newly validated build for selected revision: **{newer}**',
        f'- Official release asset: `{meta["asset_name"]}`',
        '- Compiling Rufus source: no; verified signed upstream binary is used',
        '- Source portability contract: revalidated by the build workflow',
        '- Launcher compiler: MSVC on selected Windows runner',
        '- USB operations and install/upgrade persistence: manual acceptance test required',
        '', '## Pinned shared actions',
        f'- `{cfg["package_builder"]}` (exact tested r4 source; latest visible tag: {tagged})',
        f'- `{cfg["release_publisher"]}`',
        '', 'Manual build only: this check will never publish or commit changes.'
    ]
    report = '\n'.join(lines) + '\n'
    Path('work').mkdir(exist_ok=True)
    Path('work/maintenance-report.md').write_text(report, encoding='utf-8')
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as out:
            out.write(report)


if __name__ == '__main__':
    main()
