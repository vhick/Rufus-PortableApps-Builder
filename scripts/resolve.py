#!/usr/bin/env python3
"""Resolve an official stable Rufus release and a unique x64 portable EXE. Stdlib only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config/builder.json').read_text(encoding='utf-8'))
REPO = CONFIG['upstream']
API = f'https://api.github.com/repos/{REPO}'
VERSION_RE = re.compile(r'^v?(\d+\.\d+(?:\.\d+){0,2})$', re.I)
PORTABLE_RE = re.compile(r'^rufus[-_.]?v?(\d+\.\d+(?:\.\d+){0,2})(?:[-_.]?(?:portable|p))(?:[-_.]?(?:x64|amd64))?\.exe$', re.I)
PORTABLE_RE_ALT = re.compile(r'^rufus[-_.]?v?(\d+\.\d+(?:\.\d+){0,2})[-_.]?(?:x64|amd64)[-_.]?(?:portable|p)\.exe$', re.I)
BANNED = re.compile(r'(?:beta|alpha|preview|nightly|rc\d*|test|arm|aarch64|x86|ia32|32bit)', re.I)


def api_request(url, binary=False, max_size=8_000_000):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'rufus-independent-portable-builder'}
    token = os.environ.get('GITHUB_TOKEN', '')
    if token and urllib.parse.urlsplit(url).hostname in ('api.github.com', 'github.com'):
        headers['Authorization'] = 'Bearer ' + token
    retry = 3
    for n in range(retry):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
                final = urllib.parse.urlsplit(response.url)
                allowed = {'api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com', 'raw.githubusercontent.com', 'codeload.github.com'}
                if final.scheme != 'https' or final.hostname not in allowed:
                    raise RuntimeError(f'Untrusted download redirect: {response.url}')
                buf = bytearray()
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    buf.extend(chunk)
                    if len(buf) > max_size:
                        raise RuntimeError(f'Download exceeds {max_size} bytes: {url}')
                return bytes(buf)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as ex:
            if isinstance(ex, urllib.error.HTTPError) and ex.code not in (429, 500, 502, 503, 504):
                raise
            if n + 1 == retry:
                raise
            time.sleep(2 * (n + 1))
    raise RuntimeError('Download exhausted retries')


def get_json(url):
    return json.loads(api_request(url).decode('utf-8'))


def version_tuple(value):
    match = VERSION_RE.fullmatch(value or '')
    return tuple(map(int, match.group(1).split('.'))) if match else None


def is_stable(release):
    tag = release.get('tag_name', '')
    return bool(version_tuple(tag)) and not release.get('draft') and not release.get('prerelease') and not BANNED.search(tag + ' ' + release.get('name', ''))


def select_release(releases, requested=''):
    stable = [r for r in releases if is_stable(r)]
    if requested:
        requested_version = version_tuple(requested)
        stable = [r for r in stable if r['tag_name'] == requested or (requested_version and version_tuple(r['tag_name']) == requested_version)]
    if not stable:
        raise RuntimeError(f'No matching stable Rufus release (requested={requested!r}). Never fall back to prereleases.')
    return max(stable, key=lambda r: (version_tuple(r['tag_name']), r.get('published_at') or ''))


def select_asset(release):
    tag_version = version_tuple(release['tag_name'])
    options = []
    for a in release.get('assets', []):
        name = a.get('name', '')
        match = PORTABLE_RE.fullmatch(name) or PORTABLE_RE_ALT.fullmatch(name)
        if match and not BANNED.search(name) and version_tuple(match.group(1)) == tag_version:
            url = a.get('browser_download_url', '')
            split = urllib.parse.urlsplit(url)
            expected_prefix = f'/{REPO}/releases/download/'
            if split.scheme != 'https' or split.hostname != 'github.com' or not split.path.startswith(expected_prefix):
                raise RuntimeError(f'Asset has unexpected origin: {name} {url}')
            if not isinstance(a.get('size'), int) or not 20_000 < a['size'] <= CONFIG['max_asset_bytes']:
                raise RuntimeError(f'Invalid asset size for {name}')
            options.append(a)
    if len(options) != 1:
        raise RuntimeError('Expected precisely one official x64 Rufus portable EXE, found ' + str(len(options)) + ': ' + ', '.join(a['name'] for a in options))
    return options[0]


def inspect_pe(data):
    if len(data) < 2048 or data[:2] != b'MZ':
        raise RuntimeError('Download is not a Windows PE executable')
    offset = struct.unpack_from('<I', data, 0x3c)[0]
    if offset < 0x40 or offset + 26 > len(data) or data[offset:offset + 4] != b'PE\0\0':
        raise RuntimeError('Windows PE header is invalid')
    machine = struct.unpack_from('<H', data, offset + 4)[0]
    if machine != 0x8664:
        raise RuntimeError(f'Expected x64 PE, got machine 0x{machine:04x}')


def gh_output(values):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as file:
            for k, v in values.items():
                file.write(f'{k}={v}\n')


def resolve(requested, dest):
    releases = []
    for page in (1, 2, 3):
        batch = get_json(f'{API}/releases?per_page=100&page={page}')
        if not isinstance(batch, list):
            raise RuntimeError('GitHub release API returned unexpected data')
        releases.extend(batch)
        if len(batch) < 100:
            break
    release = select_release(releases, requested)
    asset = select_asset(release)
    ver = '.'.join(map(str, version_tuple(release['tag_name'])))
    result = {
        'version': ver, 'tag': release['tag_name'], 'release_id': release['id'],
        'published_at': release.get('published_at'), 'asset_name': asset['name'],
        'asset_url': asset['browser_download_url'], 'asset_id': asset['id'],
        'asset_size': asset['size'], 'asset_digest': asset.get('digest') or '',
        'source_repository': REPO, 'release_page': release['html_url'],
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    gh_output({'version': ver, 'upstream_tag': result['tag'], 'release_id': str(release['id'])})
    print('Selected stable release:', release['tag_name'], 'asset:', asset['name'])
    return result


def download(meta, output):
    data = api_request(meta['asset_url'], binary=True, max_size=CONFIG['max_asset_bytes'])
    if len(data) != meta['asset_size']:
        raise RuntimeError(f'Asset size changed: expected {meta["asset_size"]}, received {len(data)}')
    inspect_pe(data)
    sha = hashlib.sha256(data).hexdigest()
    digest = meta.get('asset_digest', '')
    if digest:
        if not re.fullmatch('sha256:[0-9a-fA-F]{64}', digest):
            raise RuntimeError(f'Unexpected official asset digest format: {digest}')
        if digest.split(':', 1)[1].lower() != sha:
            raise RuntimeError('GitHub asset SHA256 mismatch')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise RuntimeError('Refusing to overwrite existing downloaded binary: ' + str(output))
    output.write_bytes(data)
    meta['downloaded_sha256'] = sha
    meta['digest_source'] = 'GitHub asset digest' if digest else 'local SHA256 plus Windows Authenticode verification required'
    print('Downloaded:', output, 'sha256:', sha)
    return meta


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers(dest='action', required=True)
    r = subs.add_parser('resolve'); r.add_argument('--version', default=''); r.add_argument('--output', default='work/resolve.json')
    d = subs.add_parser('download'); d.add_argument('--metadata', default='work/resolve.json'); d.add_argument('--output', default='work/official-rufus.exe')
    args = parser.parse_args()
    if args.action == 'resolve':
        resolve(args.version, Path(args.output))
    else:
        path = Path(args.metadata)
        meta = json.loads(path.read_text(encoding='utf-8'))
        download(meta, Path(args.output))
        path.write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('RUFUS RESOLUTION / DOWNLOAD FAILED: ' + str(exc), file=sys.stderr)
        sys.exit(1)
