#!/usr/bin/env python3
"""Bounded Sidecar protocol probe using unchanged baseline visibility bodies.

This is not a real-engine allocation/recovery test. Engine transaction-table,
snapshot-container, and WAL appending APIs are replaced by explicit harness state.
"""
from pathlib import Path
import ctypes
import itertools
import subprocess
import argparse
import tempfile
import json

parser = argparse.ArgumentParser()
parser.add_argument('--repo', type=Path, required=True)
ROOT = parser.parse_args().repo.resolve()
OUT = Path(tempfile.mkdtemp(prefix='sidecar-visibility-'))
EXPECTED = 'e64a04a79a5842827a124b3f8313516d0da2594c'
assert subprocess.run(['git', 'diff', '--quiet', EXPECTED, '--',
    'src/transaction/log_tran_table.c', 'src/transaction/mvcc.c',
    'src/transaction/replication.c', 'src/base/object_representation_constants.h',
    'src/storage/storage_common.h', 'src/transaction/mvcc.h'], cwd=ROOT).returncode == 0, 'baseline source changed'

def body(file, name, result):
    text = (ROOT / file).read_text()
    start = text.index('\n' + name + ' (') + 1
    brace = text.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    value = result + '\n' + text[start:end]
    return value

def macro(file, name):
    lines = (ROOT / file).read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith('#define ' + name + ' ') or line.startswith('#define ' + name + '\t') or line.startswith('#define ' + name + '('):
            selected = [line]
            while selected[-1].endswith('\\'):
                i += 1
                selected.append(lines[i])
            return '\n'.join(selected)
    raise ValueError(name)

pieces = ['''#include <cassert>
#include <cstddef>
using std::size_t;
#include <cstdint>
#include <vector>
#include <set>
using MVCCID = uint64_t;
struct THREAD_ENTRY {};
struct MVCC_REC_HEADER { int mvcc_flag; MVCCID mvcc_ins_id; MVCCID mvcc_del_id; };
struct Active { std::set<MVCCID> ids; bool is_active(MVCCID id) { return ids.count(id); } };
struct MVCC_SNAPSHOT { MVCCID lowest_active_mvccid; MVCCID highest_completed_mvccid; Active m_active_mvccs; };
struct MVCC_INFO { MVCCID id; std::vector<MVCCID> sub_ids; };
struct LOG_LSA { int pageid; };
struct LOG_REPL_RECORD { LOG_LSA lsa; int must_flush; };
struct LOG_TDES { MVCC_INFO mvccinfo; LOG_REPL_RECORD *repl_records; int cur_repl_record; };
static LOG_TDES current;
#define LOG_FIND_TDES(x) (&current)
#define LOG_FIND_THREAD_TRAN_INDEX(x) 0
#define MVCCID_NULL 0
#define perfmon_is_perf_tracking_and_active(...) false
#define perfmon_mvcc_snapshot(...) ((void)0)
static bool vacuum_is_mvccid_vacuumed(MVCCID) { return false; }
enum MVCC_SATISFIES_SNAPSHOT_RESULT { TOO_OLD_FOR_SNAPSHOT, SNAPSHOT_SATISFIED, TOO_NEW_FOR_SNAPSHOT };
enum MVCC_SATISFIES_VACUUM_RESULT { VACUUM_RECORD_REMOVE, VACUUM_RECORD_DELETE_INSID_PREV_VER, VACUUM_RECORD_CANNOT_VACUUM };
#define LSA_GT(a,b) ((a)->pageid > (b)->pageid)
#define LOG_REPL_DONT_NEED_FLUSH 0
#define NO_ERROR 0
''']
for name in ['OR_MVCC_FLAG_VALID_INSID', 'OR_MVCC_FLAG_VALID_DELID']:
    pieces.append(macro('src/base/object_representation_constants.h', name))
for name in ['MVCCID_IS_VALID', 'MVCCID_ALL_VISIBLE']:
    pieces.append(macro('src/storage/storage_common.h', name))
for name in ['MVCC_GET_INSID', 'MVCC_GET_DELID', 'MVCC_IS_FLAG_SET', 'MVCC_IS_HEADER_DELID_VALID', 'MVCC_IS_HEADER_INSID_NOT_ALL_VISIBLE', 'MVCC_IS_REC_INSERTED_BY_ME', 'MVCC_IS_REC_DELETED_BY_ME', 'MVCC_ID_PRECEDES', 'MVCC_ID_FOLLOW_OR_EQUAL']:
    pieces.append(macro('src/transaction/mvcc.h', name))
for name in ['MVCC_IS_REC_INSERTER_IN_SNAPSHOT', 'MVCC_IS_REC_DELETER_IN_SNAPSHOT', 'MVCC_IS_REC_INSERTED_SINCE_MVCCID', 'MVCC_IS_REC_DELETED_SINCE_MVCCID']:
    pieces.append(macro('src/transaction/mvcc.c', name))
extracted = [
    ('src/transaction/log_tran_table.c', 'logtb_is_current_mvccid', 'bool'),
    ('src/transaction/mvcc.c', 'mvcc_is_id_in_snapshot', 'bool'),
    ('src/transaction/mvcc.c', 'mvcc_satisfies_snapshot', 'MVCC_SATISFIES_SNAPSHOT_RESULT'),
    ('src/transaction/mvcc.c', 'mvcc_satisfies_vacuum', 'MVCC_SATISFIES_VACUUM_RESULT'),
    ('src/transaction/replication.c', 'repl_log_abort_after_lsa', 'int'),
]
for file, name, result in extracted:
    pieces.append(body(file, name, result))
pieces.append('''
extern "C" int visible(uint64_t ins, uint64_t del, uint64_t own, uint64_t sub, uint64_t low, uint64_t high, uint64_t active) {
  current.mvccinfo.id = own; current.mvccinfo.sub_ids.clear();
  if (sub) current.mvccinfo.sub_ids.push_back(sub);
  MVCC_REC_HEADER rec { OR_MVCC_FLAG_VALID_INSID | (del ? OR_MVCC_FLAG_VALID_DELID : 0), ins, del };
  MVCC_SNAPSHOT snap {low, high, {}}; if(active) snap.m_active_mvccs.ids.insert(active);
  return mvcc_satisfies_snapshot(nullptr, &rec, &snap);
}
extern "C" int vacuum(uint64_t ins, uint64_t del, uint64_t horizon) {
  MVCC_REC_HEADER rec { OR_MVCC_FLAG_VALID_INSID | (del ? OR_MVCC_FLAG_VALID_DELID : 0), ins, del };
  return mvcc_satisfies_vacuum(nullptr, &rec, horizon);
}
extern "C" int surviving_events(int rollback_lsa) {
  LOG_REPL_RECORD events[] = {{{10}, 1}, {{20}, 1}, {{30}, 1}};
  current.repl_records = events; current.cur_repl_record = 3;
  LOG_LSA point { rollback_lsa };
  repl_log_abort_after_lsa(&current, &point);
  int mask = 0;
  for (int i = 0; i < 3; ++i) if (events[i].must_flush) mask |= (1 << i);
  return mask;
}
''')
source = OUT / 'baseline_probe.cpp'
source.write_text('\n\n'.join(pieces))
subprocess.run(['g++', '-std=c++17', '-O2', '-shared', '-fPIC', str(source), '-o', str(OUT / 'baseline_probe.so')], check=True)
lib = ctypes.CDLL(str(OUT / 'baseline_probe.so'))
lib.visible.argtypes = [ctypes.c_uint64] * 7
lib.vacuum.argtypes = [ctypes.c_uint64] * 3
lib.surviving_events.argtypes = [ctypes.c_int]

def visible(header, context):
    return lib.visible(*header, *context) == 1

contexts = {
    'old_before_writer': (200, 0, 100, 100, 0),
    'old_writer_active': (200, 0, 100, 101, 100),
    'writer': (100, 0, 100, 101, 100),
    'writer_nested': (99, 100, 99, 101, 99),
    'new_after_commit': (200, 0, 101, 101, 0),
}

class State:
    def __init__(self):
        self.parents = [((10, 0), 0)]
        self.chunks = {0: (10, 0)}
        self.next_id = 1
    def copy(self):
        import copy
        return copy.deepcopy(self)
    def current(self):
        for header, value in reversed(self.parents):
            result = lib.visible(*header, *contexts['writer'])
            if result == 1:
                return value
            if result == 0:
                return None
        return None
    def mutate(self, op):
        previous = self.current()
        if op == 'hot':
            if previous is None: return
            self.parents.append(((100, 0), previous))
        elif op in ('replace', 'inline', 'delete'):
            # The design explicitly materializes required before values here.
            if previous is not None and previous >= 0:
                assert visible(self.chunks[previous], contexts['writer'])
            if previous is not None and previous >= 0:
                ins, _ = self.chunks[previous]
                self.chunks[previous] = (ins, 100)
            if op == 'replace':
                value = self.next_id
                self.next_id += 1
                self.chunks[value] = (100, 0)
                self.parents.append(((100, 0), value))
            elif op == 'inline':
                self.parents.append(((100, 0), -1))
            elif self.parents:
                self.parents.append(((100, 100), previous))
    def check(self, context):
        for header, value in reversed(self.parents):
            outcome = lib.visible(*header, *context)
            if outcome == 2: continue
            if outcome == 0: return
            if value is not None and value >= 0:
                assert visible(self.chunks[value], context), (header, value, context, self.chunks)
            return

checked = 0
for actions in itertools.product(('hot', 'replace', 'inline', 'delete'), repeat=4):
    state = State()
    savepoints = [state.copy()]
    for op in actions:
        state.mutate(op)
        savepoints.append(state.copy())
        for context in contexts.values():
            state.check(context)
            checked += 1
    for restored in savepoints:
        # Assumes physical undo restores all parent/chunk changes as required;
        # it does not model engine rollback execution or page allocation.
        for context in contexts.values():
            restored.check(context)
            checked += 1

assert lib.vacuum(10, 100, 100) != 0
assert lib.vacuum(10, 100, 101) == 0
assert lib.surviving_events(15) == 1
assert lib.surviving_events(25) == 3
assert lib.surviving_events(35) == 7

state = State()
state.mutate('replace')
state.chunks[0] = (10, 10)
try:
    state.check(contexts['old_before_writer'])
except AssertionError:
    bad_delete_rejected = True
else:
    raise AssertionError('bad deletion negative control was not rejected')

state = State()
state.mutate('replace')
state.chunks[state.current()] = (101, 0)
try:
    state.check(contexts['writer'])
except AssertionError:
    bad_identity_rejected = True
else:
    raise AssertionError('bad identity negative control was not rejected')

lease_context = contexts['writer']
before = visible((10, 0), lease_context)
after = visible((10, 100), lease_context)
assert before and not after
report = {
    'source_commit': EXPECTED,
    'extracted_functions': [x[1] for x in extracted],
    'bounded_lifecycle': {'operation_sequences': 256, 'visibility_checks': checked, 'result': 'PASS'},
    'vacuum_retains_before_horizon_and_removes_after': 'PASS',
    'rollback_replication_bookkeeping': 'PASS: rollback LSAs 15,25,35 yield event masks 1,3,7',
    'negative_controls': {'incorrect_old_delete_rejected': bad_delete_rejected, 'incorrect_child_identity_rejected': bad_identity_rejected},
    'own_delete_same_snapshot': {'before': before, 'after': after, 'classification': 'boundary observation; no established retained-VisibleRow execution'},
    'limitations': 'Extracted decision functions and bounded coordinated mutation model; no engine allocator, durable WAL, native savepoint execution, concurrent schedule, restart, or HA execution.'
}
(OUT / 'probe-result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
