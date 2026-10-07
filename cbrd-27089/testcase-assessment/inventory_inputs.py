#!/usr/bin/env python3
"""Record exact pre-edit testcase trees and the independent contract sources."""
import hashlib
import json
from pathlib import Path
import subprocess


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


engine = Path('/home/vimkim/gh/cb/pr7927-assessment-head')
public = Path('/home/vimkim/gh/cubrid-testcases/tc-pr-7927')
private = Path('/home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-7927')
head = '4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c'
base = 'fb567a629cdb390fff920542173fa36f454c74a0'
paths = ['src/loaddb/load_server_loader.cpp', 'src/loaddb/load_grammar.yy',
         'src/loaddb/load_error_handler.cpp', 'src/loaddb/load_session.cpp',
         'src/storage/heap_file.c', 'src/storage/btree.c', 'src/storage/btree_load.c',
         'src/query/vacuum.c']
manifest = {
    'engine_head': head, 'engine_base': base,
    'engine_objects': {p: {rev: git(engine, 'rev-parse', rev + ':' + p)
                          for rev in [head, base]} for p in paths},
    'testcase_trees': {},
}
for repo, dirs, pin in [
    (public, ['medium/_02_xtests'], 'bdba62aee0faec05abdd861518824c69b6c1b3c5'),
    (private, ['shell/_06_issues/_15_1h/bug_bts_15489',
               'shell/_06_issues/_25_2h/cbrd_26280',
               'shell/_35_cherry/issue_21654_server_side_loaddb/partition_tbls',
               'shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064',
               'shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075'],
     'c4b9d482fbd491a68510b2552df2c3cac91911fc'),
]:
    current = git(repo, 'rev-parse', 'HEAD')
    manifest['testcase_trees'][str(repo)] = {
        'revision': current, 'ci_revision': pin, 'status': git(repo, 'status', '--short'),
        'objects': {d: {'current': git(repo, 'rev-parse', current + ':' + d),
                        'ci': git(repo, 'rev-parse', pin + ':' + d)} for d in dirs},
    }
for key, location, paths in [
    ('manual', '/home/vimkim/gh/cubrid-manual',
     ['en/sql/partition.rst', 'en/sql/query/select.rst', 'en/admin/migration.inc']),
    ('oos_context', '/home/vimkim/gh/cubrid-oos-context',
     ['OOS-CONTEXT.md', 'docs/adr/0005-defer-oos-history-from-the-11-5-merge.md']),
]:
    repo = Path(location)
    manifest[key] = {'revision': git(repo, 'rev-parse', 'HEAD'),
                     'status': git(repo, 'status', '--short'),
                     'files': {p: digest(repo / p) for p in paths}}
ctp = Path('/home/vimkim/gh/ctp/run-sql')
manifest['ctp'] = {
    'revision': git(ctp, 'rev-parse', 'HEAD'), 'status': git(ctp, 'status', '--short'),
    'tracked_asset_hashes': {p: digest(ctp / p) for p in git(ctp, 'ls-files', 'CTP').splitlines()
                           if (ctp / p).is_file()},
}
destination = Path(__file__).parent / 'input-manifest.json'
if destination.exists():
    raise SystemExit('Refusing to overwrite the pre-edit inventory')
destination.write_text(json.dumps(manifest, indent=2) + '\n')
print('testcase trees match pinned CI:', all(
    value['current'] == value['ci'] for repo in manifest['testcase_trees'].values()
    for value in repo['objects'].values()))
