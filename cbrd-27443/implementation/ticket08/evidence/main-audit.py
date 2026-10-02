from pathlib import Path
import hashlib, json, re, subprocess, sys
attempt = Path(sys.argv[1])
engine = Path('/home/vimkim/gh/cb/CBRD-27443-fd-clean')
tests = Path('/home/vimkim/gh/cubrid-testcases-private-ex/CBRD-27443-fd-clean')
install = Path('/home/vimkim/.cub/install/CBRD-27443-fd-clean/debug_gcc')
def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()
source = (attempt/'engine-commit.txt').read_text().strip()
test_commit = (attempt/'testcase-commit.txt').read_text().strip()
assert source == '0809a480df55ac6767a905d03fa3d31edd40a93c'
for repo, commit in [(engine, source), (tests, test_commit)]:
    assert git(repo, 'rev-parse', 'HEAD') == commit
    assert not git(repo, 'status', '--short')
for name in ('engine.patch', 'testcase.patch'):
    assert (attempt/name).read_text() == ''
expected = (attempt/'expected-cases.txt').read_text().splitlines()
discovered = []
for name in git(tests, 'ls-files', 'shell/_01_utility/cbrd_27443').splitlines():
    p = Path(name)
    if p.suffix == '.sh' and p.parent.name == 'cases' and p.stem == p.parent.parent.name:
        discovered.append(str(tests/p))
assert sorted(expected) == sorted(discovered) and len(expected) == 4
modes = {'matrix','master-matrix','restart-matrix','boundary-matrix','rot','ha','repl','b-broker','b-failure','b-recovery','b-scaling','b-rot'}
reports = {}
counts = {}
roots = {}
captures = 0
foreground_captures = []
faults = []
for path in (attempt/'home/.cache').glob('fd-*/matrix.json'):
    mode = path.parent.name[3:].rsplit('.',1)[0]
    assert mode in modes and mode not in reports, mode
    d = json.loads(path.read_text())
    reports[mode] = d
    checks = d['checks']
    assert checks and all(c['pass'] is True for c in checks), mode
    assert any(word in checks[-1]['name'] for word in ('gone','reaped','removed')), mode
    counts[mode] = len(checks)
    for index,c in enumerate(d['captures']):
        assert c['launcher_rc'] is not None
        targets = set(c['caller_targets'])
        if mode == 'master-matrix' and not c['eof_s']:
            pid = int((Path(d['runtime_root']).parent/'init-master.pid').read_text())
            assert c['launcher_rc'] == 0 and c['lock_available'] is True
            assert set(c['output']) == {'stdout','stderr'}
            assert len(c['caller_holders']) == 1
            holder = c['caller_holders'][0]
            assert holder['pid'] == pid and holder['name'] == 'cub_master'
            assert holder['fds']['1'] in targets and holder['fds']['2'] in targets
            assert holder['fds']['1'].startswith('pipe:[') and holder['fds']['2'].startswith('pipe:[')
            assert not set(c['caller_targets'][:2]).intersection(holder['fds'].values())
            assert all(not targets.intersection(p['fds'].values()) for p in c['processes'] if p['pid'] != pid)
            assert any(x['name'] == 'PID1 supervisor stdout stderr contract remains attached' and x['pass'] for x in checks)
            foreground_captures.append({'mode':mode,'index':index,'pid':pid,'contract':'intentional PID1 foreground supervisor streams'})
        else:
            assert set(c['eof_s']) == set(c['output'])
            assert c['lock_available'] is True and c['caller_holders'] == []
            assert all(not targets.intersection(p['fds'].values()) for p in c['processes'])
            captures += 1
    roots[mode] = Path(d['runtime_root'])
    if 'cleanup_processes' in d:
        if mode == 'master-matrix':
            assert d['cleanup_processes'] and all(snapshot == [] for snapshot in d['cleanup_processes'])
        else:
            assert d['cleanup_processes'] == []
    for f in d.get('logging_faults', []):
        assert f['prior_failure']['mtime_ns'] != f['failure_mtime_ns']
        assert 'operation=open' in f['failure'] and len(f['failure']) == 256
        faults.append(f['label'])
assert set(reports) == modes
assert len(foreground_captures) == 1
assert len(faults) == 12 and len(set(faults)) == 12
repl = reports['repl']
assert [r['id'] for r in repl['replicated_records']] == list(range(1,16))
roots['nodeb'] = Path(repl['topology']['nodeb']['root'])
for kind in ('net','uts','mnt'):
    assert repl['topology']['nodea']['namespaces'][kind] != repl['topology']['nodeb']['namespaces'][kind]
present_paths = list((attempt/'home/.cache').glob('fd-present.*/present.json'))
assert len(present_paths) == 1
present = json.loads(present_paths[0].read_text())
assert present['launcher_rc'] == 0 and all(present['eof_after_exit_plus_2s'].values())
assert present['lock_available_while_running'] and present['holders_after_service_stop'] == []
roots['present'] = Path(present['runtime_root'])
identities = reports['matrix']['binary_sha256']
assert len(identities) == 18
for d in list(reports.values()) + [present]:
    assert d['binary_sha256'] == identities
for node in repl['topology'].values():
    assert node['sha256'] == identities
hashes = []
for obj, recorded in identities.items():
    assert sha(install/obj) == recorded == sha(attempt/'cubrid'/obj)
    for fixture, root in roots.items():
        actual = sha(root/obj)
        assert actual == recorded, (fixture,obj)
        hashes.append({'fixture':fixture,'object':obj,'sha256':actual})
result = {'source':source,'test_commit':test_commit,'expected_cases':expected,'matrix_counts':counts,
          'assertions':sum(counts.values()),'background_captures':captures,'foreground_captures':foreground_captures,'runtime_faults':faults,
          'replicated_rows':15,'install_copy_pairs':18,'actual_fixture_hashes':hashes,
          'fixtures':{k:str(v) for k,v in roots.items()}}
(attempt/'main-independent-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('actual_fixture_hashes','fixtures')},indent=2))
print('Independently verified actual fixture files:',len(hashes))
# Supplemental observations use the retained real broker fixture, not a new run.
supplemental = []
for entry in reports['b-broker']['restarts']:
    parent, child = entry['parent'], entry['after']
    assert child['fds']['0'] == '/dev/null'
    assert all(child['fds'][fd] == parent['fds'][fd] for fd in ('1','2'))
    assert entry['internal_leaks'] == []
    supplemental.append({'pid':child['pid'],'check':'null stdin, dedicated parent outputs, no internal FD'})
console = (roots['b-broker']/'log/broker-console.log').read_text()
for name in ('cub_cas','cub_proxy'):
    for fd in (1,2):
        count = console.count('BROKER-ATTEMPT-'+name+'-%d\n'%fd)
        assert count == 4000
        supplemental.append({'name':name,'fd':fd,'complete_lines':count})
result['supplemental'] = supplemental
(attempt/'main-independent-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('Supplemental checks:',len(supplemental))
