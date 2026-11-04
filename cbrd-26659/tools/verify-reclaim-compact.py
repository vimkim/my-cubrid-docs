#!/usr/bin/env python3
import argparse
import collections
import hashlib
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

CASES = {
    'a02': ('full3cycle', []),
    'a03': ('iud', ['diagnostic_cycle0_idle']),
    'a04': ('restart', ['diagnostic_cycle0_idle']),
    'a06': ('snapshot', ['diagnostic_snapshot_idle', 'diagnostic_snapshot_churn_idle']),
    'a08': ('compact_sa_original_and_dml_control', []),
    'a10': ('compact_cs_patched_control', []),
    'a11': ('abortretry', ['diagnostic_cycle0_idle']),
    'a12': ('id', ['diagnostic_cycle0_idle', 'diagnostic_after_pressure']),
    'a13': ('abort_targeted_followup', []),
    'a14': ('abort_residual_identity_checked', ['diagnostic_cycle0_idle']),
    'a15': ('abort_symbol_entry', ['diagnostic_cycle0_idle']),
}


def read_json(path):
    return json.loads(path.read_text())


def vpid(p):
    return p['vol'], p['page']


def events(attempt):
    result = []
    for path in sorted(attempt.glob('gdb-*.jsonl')):
        for line in path.read_text().splitlines():
            result.append(json.loads(line))
    return result


def census(prefix, samples):
    paths = [Path(str(prefix) + suffix) for suffix in ('.census.json', '.allocation.json', '.pages.bin')]
    if not all(p.exists() for p in paths):
        return {'status': 'pending', 'missing': [p.name for p in paths if not p.exists()]}, None
    data, allocation = map(read_json, paths[:2])
    raw = paths[2].read_bytes()
    pages = data['pages']
    if len(raw) != len(pages) * 16384:
        raise ValueError(f'{paths[2]}: length {len(raw)} does not match {len(pages)} pages')
    if [vpid(p) for p in pages] != [vpid(p) for p in allocation['pages']]:
        raise ValueError(f'{prefix}: census and allocation roster differ')
    empty = {}
    counts = collections.Counter()
    for i, expected in enumerate(pages):
        b = raw[i * 16384:(i + 1) * 16384]
        _, page, vol = struct.unpack_from('<Qih', b)
        lsa = [int.from_bytes(b[:6], 'little', signed=True), struct.unpack_from('<h', b, 6)[0]]
        if b[:8] != b[-8:] or b[15] & 3:
            raise ValueError(f'{prefix}: watermark or encryption mismatch at {i}')
        typ = b[14]
        sticky = (vol, page) == vpid(allocation['sticky'])
        decoded = dict(vol=vol, page=page, ptype=typ, sticky=sticky, lsa=lsa,
                       num_slots=0, num_records=0, record_bytes=0, total_free=0, contiguous_free=0)
        if typ == 14:
            slots, records = struct.unpack_from('<hh', b, 32)
            align = struct.unpack_from('<H', b, 38)[0]
            total, cont, offset = struct.unpack_from('<iii', b, 40)
            if not (0 <= records <= slots <= 4096 and align in (1, 2, 4, 8) and 0 <= cont <= total <= 16312 and 32 <= offset <= 16344 - slots * 4):
                raise ValueError(f'{prefix}: invalid slotted header {(vol, page)}')
            if not sticky and not (lsa[0] >= 0 and 0 <= lsa[1] < 16344):
                raise ValueError(f'{prefix}: invalid data-page LSA {(vol, page)}')
            spans = []
            for j in range(slots):
                slot = struct.unpack_from('<I', b, 32 + 16344 - (j + 1) * 4)[0]
                start, length = slot & 0x3fff, (slot >> 14) & 0x3fff
                if start:
                    if not (start >= 32 and length > 0 and start + length <= 16344 - slots * 4):
                        raise ValueError(f'{prefix}: invalid slot {(vol, page, j)}')
                    spans.append((start, start + length))
            spans.sort()
            if len(spans) != records or any(a[1] > z[0] for a, z in zip(spans, spans[1:])):
                raise ValueError(f'{prefix}: slot overlap/count {(vol, page)}')
            decoded.update(num_slots=slots, num_records=records, record_bytes=sum(y-x for x,y in spans), total_free=total, contiguous_free=cont)
            if not sticky and records == 0:
                empty[(vol, page)] = tuple(lsa)
        elif typ != 1:
            raise ValueError(f'{prefix}: unexpected page type {typ}')
        if decoded != expected:
            raise ValueError(f'{prefix}: raw/census mismatch at {i}: {decoded} != {expected}')
        counts['sticky' if sticky else str(typ)] += 1
    if counts['sticky'] != 1 or counts['1'] != allocation['table_pages'] or counts['14'] + counts['sticky'] != allocation['user_pages']:
        raise ValueError(f'{prefix}: allocation counts differ')
    if data['user_pages'] != allocation['user_pages'] or data['table_pages'] != allocation['table_pages'] or data['allocated_pages'] != len(pages):
        raise ValueError(f'{prefix}: census totals differ')
    rejected, missing = set(), 0
    keys = ['vpid.volid', 'vpid.pageid', 'page_lsa.pageid', 'page_lsa.offset', 'horizon.pageid', 'horizon.offset', 'rollback_delete_lsa.pageid', 'rollback_delete_lsa.offset']
    for event in samples:
        if event.get('event') != 'oos_reclaim_lsa_gate_passes':
            continue
        if not all(isinstance(event.get(k), int) for k in keys):
            missing += 1
            continue
        vp = event[keys[0]], event[keys[1]]
        pl = event[keys[2]], event[keys[3]]
        horizon = event[keys[4]], event[keys[5]]
        rollback = event[keys[6]], event[keys[7]]
        allowed = pl < horizon or (pl == horizon == rollback and rollback != (-1, -1))
        if vp in empty and empty[vp] == pl and not allowed:
            rejected.add(vp)
    return {'status': 'observed', 'allocated_pages': len(pages), 'user_pages': allocation['user_pages'], 'sectors': allocation['sector_count'], 'empty_pages': len(empty), 'matched_rejected_vpids': sorted(rejected), 'unmatched_vpids': sorted(set(empty) - rejected), 'incomplete_gate_samples': missing}, (pages, allocation, empty)


def runner(attempt):
    run = attempt / 'CTP/result/shell/current_runtime_logs'
    result = {}
    x = run / 'test-shell.xml'
    if x.exists() and x.stat().st_size:
        root = ET.parse(x).getroot()
        result['xml_cases'] = [{'name': t.get('name'), 'file':t.get('file'), 'verdict': 'FAIL' if t.find('failure') is not None or t.find('error') is not None else 'SKIP' if t.find('skipped') is not None else 'PASS'} for t in root.iter('testcase')]
    else:
        result['xml_cases'] = 'pending'
    for name in ['dispatch_tc_ALL.txt', 'dispatch_tc_FIN_local.txt', 'test_status.data']:
        p = run / name
        result[name] = p.read_text().splitlines() if p.exists() else None
    p = attempt / 'exit.status'
    result['runner_exit'] = p.read_text().strip() if p.exists() else None
    if result['runner_exit'] is not None:
        identity = read_json(attempt / 'identity.json')
        if identity['source_engine'] != 'e3589ae42d42b04eb020e1ae43e165b01d31b12a' or identity['tc_head'] != '01df2600ac75180812451462b5c044cfa56b732a':
            raise ValueError(f'{attempt}: source identity differs')
        if hashlib.sha256((attempt / 'conf/shell.conf').read_bytes()).hexdigest() != identity['config_sha256']:
            raise ValueError(f'{attempt}: configuration changed')
        expected = (attempt / 'expected-cases.txt').read_text().splitlines()
        if len(expected) != 1 or result['dispatch_tc_ALL.txt'] != expected or result['dispatch_tc_FIN_local.txt'] != expected:
            raise ValueError(f'{attempt}: exact dispatch/FIN mismatch')
        if not isinstance(result['xml_cases'], list) or len(result['xml_cases']) != 1:
            raise ValueError(f'{attempt}: missing or extra XML case')
        if result['xml_cases'][0]['file'] != expected[0] or Path(result['xml_cases'][0]['name']).name != Path(expected[0]).name:
            raise ValueError(f'{attempt}: XML case identity differs')
        status = dict(line.split('=', 1) for line in result['test_status.data'])
        verdict = result['xml_cases'][0]['verdict']
        if verdict != ('PASS' if attempt.name == 'a10' else 'FAIL'):
            raise ValueError(f'{attempt}: the recorded native verdict changed')
        if status != {'total_case_count':'1', 'total_executed_case_count':'1', 'total_success_case_count':str(int(verdict == 'PASS')), 'total_fail_case_count':str(int(verdict == 'FAIL')), 'total_skip_case_count':str(int(verdict == 'SKIP'))}:
            raise ValueError(f'{attempt}: status and XML differ')
        observation = read_json(attempt / 'observation.json')
        if result['runner_exit'] != '0' or observation['deadline_outcome'] or observation['remaining_owned_processes'] or observation['remaining_observed_namespace_holders']:
            raise ValueError(f'{attempt}: invocation or owned cleanup incomplete')
        if not all(observation['observed_private_namespace_inodes'].values()) or not (run / 'feedback.log').is_file():
            raise ValueError(f'{attempt}: containment or feedback evidence missing')
    return result or {'status': 'pending'}


def journal(attempt, scenario):
    base = attempt / 'evidence' / scenario
    p = base / 'oos11.journal.log'
    if not p.exists():
        return {'status': 'pending'}
    entries = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    cleanup = read_json(base / 'oos11.cleanup.log') if (base / 'oos11.cleanup.log').exists() else None
    if cleanup is not None and (cleanup['errors'] or any(not value for key, value in cleanup.items() if key != 'errors')):
        raise ValueError(f'{attempt}: testcase owned cleanup incomplete')
    return {'events': [{'event': e.get('event'), 'phase': e.get('phase'), 'message': e.get('message')} for e in entries if e.get('event') in ('PASS', 'FAIL')], 'cleanup': cleanup}


def compact(attempt):
    dirs = list((attempt / 'CTP/result/shell/case-logs').glob('*/cases/case'))
    if not dirs:
        return {'status': 'pending'}
    d = dirs[0]
    physical = {}
    for p in sorted(d.glob('oos12.*.physical.log')):
        fields = {k: int(v) for k, v in re.findall(r'\b(reprid|stored_length|flags)\s*:\s*(\d+)', p.read_text())}
        physical[p.name] = fields
    checks = {p.name: p.read_text().strip() for p in sorted(d.glob('gap.*.check.log'))}
    expected = {'a08': {'old_representation': (1, 3040, 1), 'materialized': (2, 5544, 0), 'diagnostic_update': (2, 2576, 13)}, 'a10': {'materialized': (2, 2576, 13)}}[attempt.name]
    physical_matches = {}
    for phase, values in expected.items():
        matches = [fields for filename, fields in physical.items() if f'.{phase}.physical.log' in filename]
        physical_matches[phase] = len(matches) == 1 and tuple(matches[0].get(k) for k in ('reprid', 'stored_length', 'flags')) == values
    if not all(physical_matches.values()):
        raise ValueError(f'{attempt}: compact physical observation changed')
    cleanup = d / 'oos12.cleanup.log'
    cleanup = read_json(cleanup)
    if cleanup['failures'] or cleanup['normal_stop_failures'] or any(cleanup['owned_server_pids'].values()) or any(not cleanup[key] for key in ('config_restored','owned_command_groups_absent','owned_directories_absent','owned_registry_absent')):
        raise ValueError(f'{attempt}: compact owned cleanup incomplete')
    controller = (d / 'utility.controller.log').read_text().splitlines()
    for phase in ('initial.full_values','old_representation.full_values','materialized.full_values','materialized.owner_mapping','diagnostic_update.full_values','diagnostic_update.owner_presence','diagnostic_update.owner_mapping'):
        if 'PASS ' + phase not in controller:
            raise ValueError(f'{attempt}: missing successful {phase}')
    expected_owner = 'FAIL' if attempt.name == 'a08' else 'PASS'
    if expected_owner + ' materialized.owner_presence' not in controller:
        raise ValueError(f'{attempt}: changed materialized owner result')
    return {'physical': physical, 'expected_physical_matches': physical_matches, 'checks': checks, 'cleanup': cleanup}



def pressure(before, after, barrier_path):
    if not before or not after or not barrier_path.exists():
        return {'status': 'pending'}
    _, ba, empty = before
    ap, aa, _ = after
    barrier = tuple(read_json(barrier_path))
    after_by_id = {vpid(p): p for p in ap}
    old = [after_by_id.get(v) for v in empty]
    old_sectors = {(s['vol'], s['sector']) for s in ba['sectors']}
    new_sectors = {(s['vol'], s['sector']) for s in aa['sectors']} - old_sectors
    new_live = [p for p in ap if (p['vol'], p['page'] // 64) in new_sectors and p['ptype'] == 14 and not p['sticky'] and p['num_records']]
    first = min((tuple(p['lsa']) for p in new_live), default=None)
    result = {'status': 'observed', 'barrier': barrier, 'old_empty_pages': len(old), 'old_empty_now_occupied': sum(bool(p and p['num_records']) for p in old), 'old_lsa_at_or_after_barrier': sum(bool(p and tuple(p['lsa']) >= barrier) for p in old), 'first_new_sector_live_lsa': first, 'old_lsa_before_first_new_sector_live': sum(bool(p and first and tuple(p['lsa']) < first) for p in old), 'before_sectors': len(old_sectors), 'after_sectors': len(aa['sectors']), 'after_live_records': sum(p['num_records'] for p in ap if p['ptype'] == 14 and not p['sticky'])}
    if not old or any(result[key] != len(old) for key in ('old_empty_now_occupied','old_lsa_at_or_after_barrier','old_lsa_before_first_new_sector_live')) or result['before_sectors'] != 2 or result['after_sectors'] != 3 or result['after_live_records'] != 141:
        raise ValueError('pressure control does not establish the recorded reuse ordering')
    return result


def main():
    parser = argparse.ArgumentParser(description='Read native verdicts, diagnostic traces, and raw OOS pages; do not infer a testcase pass.')
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    result = {'root': str(args.root), 'engine': 'e3589ae42d42b04eb020e1ae43e165b01d31b12a', 'original_tc': '01df2600ac75180812451462b5c044cfa56b732a', 'attempts': {}}
    decoded = {}
    for name, (scenario, captures) in CASES.items():
        attempt = args.root / name
        sample = events(attempt)
        item = {'scenario': scenario, 'runner': runner(attempt), 'gdb_event_counts': dict(collections.Counter(e.get('event') for e in sample))}
        if item['runner']['runner_exit'] is None:
            raise ValueError(f'{attempt}: retained invocation incomplete')
        if name in ('a13', 'a14'):
            item['residual_page_events'] = [e for e in sample if 'residual_page' in e.get('event', '')]
            item['residual_status'] = 'excluded_target_mismatch'
        if name == 'a15':
            undo = [e for e in sample if e.get('event') == 'undo_delete_entry']
            candidates = [e for e in sample if e.get('event') == 'candidate_entry']
            item['symbol_entry'] = {'undo': undo, 'candidates': candidates, 'returns_observed': sum(e.get('event','').endswith('_return') and e.get('event') != 'batch_return' for e in sample)}
        if captures:
            capture_scenario = 'abortretry' if name in ('a14','a15') else scenario
            item['journal'] = journal(attempt, capture_scenario)
            if item['journal'].get('cleanup') is None:
                raise ValueError(f'{attempt}: retained journal or cleanup missing')
            item['censuses'] = {}
            for capture in captures:
                summary, pages = census(attempt / 'evidence' / capture_scenario / ('oos11.' + capture), sample)
                if summary['status'] != 'observed':
                    raise ValueError(f'{attempt}: retained raw census missing: {summary}')
                item['censuses'][capture] = summary
                decoded[(name, capture)] = pages
        if name in ('a08', 'a10'):
            item['compact'] = compact(attempt)
        result['attempts'][name] = item
    result['id_pressure'] = pressure(decoded.get(('a12', 'diagnostic_cycle0_idle')), decoded.get(('a12', 'diagnostic_after_pressure')), args.root / 'a12/evidence/id/oos11.diagnostic_barrier.lsa.json')
    if result['id_pressure']['status'] != 'observed':
        raise ValueError('retained pressure observation missing')
    abort_pages = decoded.get(('a15', 'diagnostic_cycle0_idle'))
    if abort_pages:
        _, _, empty = abort_pages
        entries = result['attempts']['a15']['symbol_entry']
        checks = []
        for page in (1312,1313):
            undo = [e for e in entries['undo'] if e.get('page') == page and e.get('vol') == 1 and e.get('before_records') == 1 and 'log_rollback' in e.get('callers',[])]
            growth = [e for e in entries['candidates'] if e.get('vpid.pageid') == page and e.get('vpid.volid') == 1 and e.get('caller') == 'oos_reclaim_sweep_step']
            lsa = empty.get((1,page))
            blocked = [e for e in growth if lsa and lsa > (e['horizon.pageid'], e['horizon.offset'])]
            if not undo or not blocked:
                raise ValueError(f'rollback residual page {page} lacks entry, raw emptiness, or restrictive sampled horizon')
            checks.append({'vpid':[1,page], 'raw_lsa':lsa, 'undo_calls':len(undo), 'growth_entries_with_older_horizon':len(blocked), 'final_reclaim_enum_observed':False})
        result['abort_residual_entry_crosscheck'] = checks
    result['kind'] = 'retained_evidence_crosscheck'
    result['complete'] = all(item['runner']['runner_exit'] is not None for item in result['attempts'].values())
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, ET.ParseError) as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        sys.exit(1)
