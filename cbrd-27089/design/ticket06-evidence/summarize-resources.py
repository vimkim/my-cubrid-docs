#!/usr/bin/env python3
"""Summarize validated debugger observations; omit warmups, never interpret their timings."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
reports = ('baseline-diagnostic-final', 'candidate-diagnostic-final')
series = []
for name in reports:
    report = json.loads((root / (name + '.json')).read_text())
    assert all(r['exit_code'] == 0 for r in report['records'])
    values, pending = {}, None
    for line in report['records'][1]['output'].splitlines():
        if line.startswith('PR7600_DIAGNOSTIC '):
            pending = json.loads(line.removeprefix('PR7600_DIAGNOSTIC '))
            assert not pending['errors'], pending['errors']
        elif line.startswith('PR7600_SAMPLE '):
            sample = json.loads(line.removeprefix('PR7600_SAMPLE '))
            if sample['rep'] == 0:
                assert pending is not None
                values[sample['workload']] = pending['counts']
            pending = None
    assert len(values) == 9
    series.append(values)
keys = ('full_row_transforms', 'probe_row_serialized_bytes', 'grown_record_copy_bytes',
        'record_buffer_malloc_acquired_bytes', 'private_allocation_acquired_bytes',
        'routing_copyarea_lease_acquired_bytes', 'tracked_temporary_peak_bytes',
        'oos_payload_serialized_bytes', 'oos_insert_many_calls', 'effective_key_codec_bytes',
        'tracked_bytes_outstanding_at_end')
for workload in series[0]:
    print(workload + ' (two writes):')
    for key in keys:
        print(f'  {key}: {series[0][workload].get(key, 0)} -> {series[1][workload].get(key, 0)}')
