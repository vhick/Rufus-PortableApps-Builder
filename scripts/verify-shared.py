#!/usr/bin/env python3
"""Verify selected shared action tag contracts, do not upgrade automatically."""
import hashlib
import re
import sys
from resolve import api_request

ACTIONS = [
    ('vhick/Portable-Package-Builder', 'v1.0.0', ('source-dir', 'output-dir', 'engine', 'running-exe', 'package-revision', 'official-tool-url', 'official-tool-sha256'), ('installer-file', 'installer-sha256')),
    ('vhick/portable-release-publisher', 'v1.1.1', ('files', 'tag', 'release-title', 'tag-prefix', 'keep-releases', 'prune', 'dry-run'), ()),
]

def main():
    for repo, tag, inputs, outputs in ACTIONS:
        data = api_request(f'https://raw.githubusercontent.com/{repo}/{tag}/action.yml', max_size=100_000)
        text = data.decode('utf-8')
        if 'using: composite' not in text:
            raise RuntimeError(repo + ': expected composite action; interface changed')
        for field in inputs:
            if not re.search(r'^  ' + re.escape(field) + r':\s*$', text, re.M):
                raise RuntimeError(repo + ': required input missing: ' + field)
        for field in outputs:
            if not re.search(r'^  ' + re.escape(field) + r':\s*$', text, re.M):
                raise RuntimeError(repo + ': required output missing: ' + field)
        print(repo + '@' + tag, 'interface VERIFIED; action.yml sha256:', hashlib.sha256(data).hexdigest())

if __name__ == '__main__':
    try: main()
    except Exception as error:
        print('SHARED ACTION INTERFACE PRECHECK FAILED:', error, file=sys.stderr)
        sys.exit(1)
