#!/usr/bin/env python3
"""Read-only scoped retained-state inventory; never infer inactivity."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

worktree = Path('/home/vimkim/gh/cb/pr7925-02-record-owner')
evidence = Path('/home/vimkim/tmp/pr7925-ticket02-evidence')
selected = evidence / 'selected-workenv'
selected.mkdir(exist_ok=True)

def command(args, output):
    result = subprocess.run(args, cwd=worktree, text=True, capture_output=True)
    (evidence / output).write_text(result.stdout + result.stderr)
    return {'args': args, 'exit_code': result.returncode, 'receipt': output}

commands = [
    command(['git', 'status', '--short', '--untracked-files=all'], 'status-final.txt'),
    command(['git', 'status', '--short', '--ignored'], 'ignored-top-final.txt'),
    command(['git', 'status', '--short', '--ignored', '--untracked-files=all'], 'ignored-all-final.txt'),
    command(['git', '-C', 'cubrid-cci', 'status', '--short', '--untracked-files=all'], 'cci-status-final.txt'),
    command(['direnv', 'exec', '.', 'cub-workenv', 'env', '--worktree', str(worktree)], 'workenv-env-final.log'),
    command(['direnv', 'exec', '.', 'cub-workenv', 'doctor', '--worktree', str(worktree)], 'workenv-doctor-final.log'),
]
metadata = []
for relative in ('state.json', 'env.sh', 'databases/databases.txt', 'conf/cubrid.conf', 'conf/cubrid_broker.conf'):
    source = worktree / '.cub-workenv' / relative
    target = selected / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    metadata.append({'path': str(source), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'copy': str(target)})
state = json.loads((worktree / '.cub-workenv/state.json').read_text())
allocations_path = Path(state['state_home']) / 'allocations.json'
allocations = json.loads(allocations_path.read_text())
def selected_allocations(value):
    if isinstance(value, dict):
        if value.get('worktree') == str(worktree):
            return [value]
        return [match for entry in value.values() for match in selected_allocations(entry)]
    if isinstance(value, list):
        return [match for entry in value for match in selected_allocations(entry)]
    return []
(selected / 'allocation-selected.json').write_text(json.dumps(selected_allocations(allocations), indent=2) + '\n')

def entries(root):
    result = []
    if not root.exists():
        return result
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(directory) / name
            try:
                info = path.lstat()
                entry = {'path': str(path), 'bytes': info.st_size, 'mode': stat.filemode(info.st_mode), 'mtime_ns': info.st_mtime_ns}
                if path.is_symlink():
                    entry['symlink_target'] = os.readlink(path)
                result.append(entry)
            except OSError as error:
                result.append({'path': str(path), 'inspection_error': str(error)})
    return result

roots = [worktree / '.cub-workenv', Path(state['allocation']['tmp'])]
roots += [Path('/home/vimkim/tmp') / name for name in ('cubrid-workspace-oos-MgSSTA', 'cubrid-workspace-oos-6eV16a', 'cubrid-workspace-oos-1bS3R3', 'cubrid-workspace-oos-88DIyv')]
inventories = [{'root': str(root), 'entries': entries(root)} for root in roots]
symlinks = [{'path': str(path), 'target': os.readlink(path)} for path in sorted(worktree.iterdir()) if path.is_symlink()]
ignored = (evidence / 'ignored-all-final.txt').read_text().splitlines()
ignored_counts = Counter(line.removeprefix('!! ').split('/')[0] for line in ignored)
core_paths = []
for root in [worktree / 'build_preset_debug_gcc', *roots, Path(state['install'])]:
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            if name == 'core' or name.startswith('core.') or name.endswith('.core'):
                path = Path(directory) / name
                try:
                    with path.open('rb') as stream:
                        header = stream.read(20)
                    byteorder = 'little' if len(header) > 5 and header[5] == 1 else 'big'
                    if header[:4] == b'\x7fELF' and int.from_bytes(header[16:18], byteorder) == 4:
                        core_paths.append(str(path))
                except OSError:
                    pass
out = {'recorded_utc': datetime.now(timezone.utc).isoformat(), 'worktree': str(worktree), 'state': state,
       'commands': commands, 'metadata': metadata, 'inventories': inventories, 'ignored_file_counts': dict(ignored_counts),
       'top_symlinks': symlinks, 'core_paths_in_selected_roots': sorted(set(core_paths)),
       'cleanup': 'No database, process, IPC, socket, install, branch or worktree removal. Doctor ownership uncertainty preserved; no inactivity or disposal claim.'}
(evidence / 'retained-inventory.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'commands': commands, 'ignored_file_counts': dict(ignored_counts), 'inventories': [{'root': item['root'], 'entries': len(item['entries'])} for item in inventories], 'core_paths': core_paths}))
