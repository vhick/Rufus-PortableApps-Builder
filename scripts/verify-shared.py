#!/usr/bin/env python3
"""Fail closed if the immutable shared packager/publisher contracts change.

Uses the exact GitHub commit that passed PortableApps.com Installer 3.9.24
source-compiler smoke tests, not the outdated public v1.0.0 release or a
mutable branch. No installer executable is fetched here.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

from resolve import api_request

PACKAGER_COMMIT = '78da3c258bd7da63740d94b4b40902dde82f7df3'
ACTIONS = [
    ('vhick/Portable-Package-Builder', PACKAGER_COMMIT,
     ('source-dir', 'output-dir', 'engine', 'running-exe', 'package-revision', 'official-source-dir'),
     ('installer-file', 'installer-sha256', 'official-installer-file', 'official-installer-sha256',
      'custom-installer-file', 'custom-installer-sha256')),
    ('vhick/portable-release-publisher', 'v1.1.1',
     ('files', 'tag', 'release-title', 'tag-prefix', 'keep-releases', 'prune', 'dry-run'), ())
]


def main():
    config = json.loads(Path('config/builder.json').read_text(encoding='utf-8'))
    expected = 'vhick/Portable-Package-Builder@' + PACKAGER_COMMIT
    if config['package_builder'] != expected:
        raise RuntimeError('config/builder.json must pin the reviewed official-source packager commit')
    for repo, tag, inputs, outputs in ACTIONS:
        data = api_request(f'https://raw.githubusercontent.com/{repo}/{tag}/action.yml', max_size=100_000)
        source = data.decode('utf-8')
        if 'using: composite' not in source:
            raise RuntimeError(repo + ': expected composite action; interface changed')
        for section, fields in [('inputs', inputs), ('outputs', outputs)]:
            for field in fields:
                if not re.search(r'^  ' + re.escape(field) + r':\s*$', source, re.M):
                    raise RuntimeError(repo + ': required ' + section + ' field missing: ' + field)
        if repo.endswith('Portable-Package-Builder') and 'official-tool-url' in source:
            raise RuntimeError('Old downloading packager detected unexpectedly')
        print(repo + '@' + tag, 'interface VERIFIED; action.yml sha256:', hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('SHARED ACTION INTERFACE PRECHECK FAILED:', error, file=sys.stderr)
        sys.exit(1)
