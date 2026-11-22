#!/usr/bin/env python3
"""Fail-closed, layout-independent audit of a checked-out official Rufus release."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def audit_source(path, version, commit=''):
    path = path.resolve()
    if not (path / '.git').is_dir():
        raise RuntimeError('Expected a real git checkout of the official Rufus release tag')
    if not commit:
        commit = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise RuntimeError('Unexpected source commit identity')
    sources = [p for p in path.rglob('*') if p.is_file() and p.suffix.lower() in ('.c', '.cpp', '.h', '.ini') and '.git' not in p.parts]
    if len(sources) > 10000:
        raise RuntimeError('Too many possible source files; source structure requires review')
    ini_docs = []
    source_references = []
    portable_code = []
    for item in sources:
        if item.stat().st_size > 4_000_000:
            continue
        text = item.read_text(encoding='utf-8', errors='replace')
        norm = text.lower()
        if item.name.lower() == 'rufus.ini' and 'portable mode' in norm and 'registry' in norm:
            ini_docs.append(item.relative_to(path).as_posix())
        if item.suffix.lower() in ('.c', '.cpp', '.h') and 'rufus.ini' in norm:
            source_references.append(item.relative_to(path).as_posix())
            if 'ini_flags' in norm or ('portable' in norm and 'registry' in norm):
                portable_code.append(item.relative_to(path).as_posix())
    if len(ini_docs) != 1:
        raise RuntimeError('Portable INI contract missing or ambiguous in official tagged source; review before release')
    if not portable_code:
        raise RuntimeError('Rufus source no longer demonstrates INI/portable handling; release blocked')
    # A source-only audit is not equivalent to executing destructive USB operations.
    detected = []
    for name in ('rufus.sln', 'Makefile.am', 'configure.ac', 'Cargo.lock', 'package-lock.json', 'go.mod', 'pyproject.toml'):
        if any(p.name == name for p in path.rglob(name) if '.git' not in p.parts):
            detected.append(name)
    result = {
        'upstream_version': version, 'source_commit': commit,
        'ini_contract_files': ini_docs, 'implementation_references': source_references,
        'portable_code_files': portable_code, 'build_manifests_detected': detected,
        'distribution_mode': 'official release asset; no upstream compilation required',
        'source_check': 'PASS',
        'runtime_host_behavior': 'NOT VERIFIED; see docs/PORTABILITY-AUDIT.md',
    }
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--metadata', default='work/resolve.json')
    parser.add_argument('--output', default='work/source-audit.json')
    args = parser.parse_args()
    try:
        meta = json.loads(Path(args.metadata).read_text(encoding='utf-8'))
        result = audit_source(Path(args.source), meta['version'])
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print('Rufus upstream source portability contract: PASS', result['source_commit'])
    except Exception as exc:
        print('RUFUS UPSTREAM SOURCE CONTRACT FAILED:', exc, file=sys.stderr)
        sys.exit(1)
