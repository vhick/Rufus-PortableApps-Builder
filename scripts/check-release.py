#!/usr/bin/env python3
"""Avoid redundant expensive work and protect immutable/known-good Releases."""
import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
from resolve import API, get_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--error-if-exists', action='store_true')
    a = parser.parse_args()
    tag = f'portable-v{a.version}-{a.revision}'
    repository = os.environ.get('GITHUB_REPOSITORY', '')
    if not repository:
        raise RuntimeError('GITHUB_REPOSITORY is not set')
    exists = False
    try:
        release = get_json('https://api.github.com/repos/' + repository + '/releases/tags/' + tag)
        exists = bool(release.get('id'))
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
    if a.error_if_exists and exists:
        raise RuntimeError('Existing immutable release ' + tag + '; choose a different revision')
    if a.force and exists:
        raise RuntimeError('Cannot force-overwrite existing immutable release: ' + tag + '. Increment config/builder.json package_revision first.')
    skip = exists
    print('Planned tag:', tag, '| already published:', exists, '| skip:', skip)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as out:
            out.write(f'skip={str(skip).lower()}\nrelease_tag={tag}\n')
    if skip and os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as out:
            out.write(f'### Skipped unchanged release: `{tag}`\nNo package overwritten; use a new package revision to rebuild.\n')

if __name__ == '__main__':
    try: main()
    except Exception as error:
        print('IMMUTABLE RELEASE GUARD:', error, file=sys.stderr)
        sys.exit(1)
