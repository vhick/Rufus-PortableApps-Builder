#!/usr/bin/env python3
"""Read-only update report. No commits, arbitrary upgrades or publishing."""
import json
import os
from pathlib import Path
from resolve import resolve, get_json, API


def main():
    meta = resolve('', Path('work/maintenance-release.json'))
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    releases = get_json('https://api.github.com/repos/' + repo + '/releases?per_page=100') if repo else []
    managed = [r for r in releases if r.get('tag_name', '').startswith('portable-v') and not r.get('draft')]
    latest = managed[0]['tag_name'] if managed else '(no known-good publication yet)'
    expected_tag = 'portable-v' + meta['version'] + '-' + json.loads(Path('config/builder.json').read_text(encoding='utf-8'))['package_revision']
    newer = expected_tag not in {r['tag_name'] for r in managed}
    package_tags = []
    for upstream, key in [('vhick/Portable-Package-Builder', 'v1.0.0'), ('vhick/portable-release-publisher', 'v1.1.1')]:
        try:
            tags = get_json('https://api.github.com/repos/' + upstream + '/tags?per_page=10')
            package_tags.append(f'{upstream}: pinned {key}; latest remote visible tag {tags[0]["name"] if tags else "none"} (do not auto-upgrade)')
        except Exception as ex:
            package_tags.append(upstream + ': update check unavailable: ' + str(ex))
    lines = [
        '# Rufus read-only maintenance report', '',
        f'- Latest official stable Rufus: `{meta["tag"]}`',
        f'- Latest existing builder release: `{latest}`',
        f'- Need newly validated build for selected revision: **{newer}**',
        '- Official release asset: `' + meta['asset_name'] + '`',
        '- Compiling Rufus source: no; official signed binary is used',
        '- Source portability contract: revalidated by the build workflow',
        '- Upstream app binary dependencies: embedded; no external runtime package manager',
        '- Launcher compiler: Visual Studio MSVC auto-detected on selected Windows runner',
        '- Important: Windows system and USB operations cannot be safely CI simulated',
        '', '## Pinned shared actions', *['- ' + x for x in package_tags],
        '', 'Manual build only: this maintenance check will not publish or commit changes.'
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
