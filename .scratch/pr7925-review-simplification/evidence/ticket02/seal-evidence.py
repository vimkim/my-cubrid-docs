#!/usr/bin/env python3
"""Copy read-only review receipts and seal stable ticket evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

evidence = Path('/home/vimkim/tmp/pr7925-ticket02-evidence')
docs = Path('/home/vimkim/gh/my-cubrid-docs-pr7925-orchestration/.scratch/pr7925-review-simplification/evidence')
for phase, source in (('initial', 'whole-review-round-1'), ('final', 'whole-review-final')):
    target = evidence / 'reviews' / phase
    target.mkdir(parents=True, exist_ok=True)
    for name in ('spec.md', 'standards.md'):
        shutil.copy2(docs / source / name, target / name)

def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()

installation = Path('/home/vimkim/.cub/install/pr7925-02-record-owner/debug_gcc')
build = Path('/home/vimkim/gh/cb/pr7925-02-record-owner/build_preset_debug_gcc')
paths = [installation / name for name in ('bin/csql', 'bin/cubrid', 'bin/cub_server', 'lib/libcubridsa.so', 'lib/libcubrid.so', 'lib/libcubridcs.so')]
paths += [build / 'bin' / name for name in ('test_oos_workspace', 'test_oos_sql_workspace_bytes', 'test_oos_sql_deferred_write')]
binary_receipt = {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': '1932b3ec3d1b83bec83b7de1a6dd482f3a03b63d', 'build_receipt': 'build-repair-committed.log', 'files': []}
for path in paths:
    info = path.stat()
    binary_receipt['files'].append({'path': str(path), 'resolved_path': str(path.resolve()), 'bytes': info.st_size, 'mtime_ns': info.st_mtime_ns, 'sha256': digest(path)})
(evidence / 'binary-receipt-final.json').write_text(json.dumps(binary_receipt, indent=2) + '\n')
files = []
for path in sorted(evidence.rglob('*')):
    if path.is_file() and path.name != 'evidence-manifest.json':
        files.append({'path': str(path.relative_to(evidence)), 'bytes': path.stat().st_size, 'sha256': digest(path)})
manifest = {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'final_source': '1932b3ec3d1b83bec83b7de1a6dd482f3a03b63d', 'files': files}
(evidence / 'evidence-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({'binary_files': len(binary_receipt['files']), 'evidence_files': len(files), 'report_sha256': digest(evidence / 'report.md'), 'manifest_sha256': digest(evidence / 'evidence-manifest.json')}))
