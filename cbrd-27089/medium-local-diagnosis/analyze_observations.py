#!/usr/bin/env python3
"""Retain original conversion plans and target rows from successful GDB probes."""
import json
from pathlib import Path
import re


ROOT = Path('/home/vimkim/tmp/pr7927-medium-diagnosis-20261007')
DEST = Path(__file__).with_name('evidence')
NAMES = ['to_char_order_by', 'to_number_order_by', 'to_timestamp_order_by']


def main():
    plans = {}
    for name in NAMES:
        sides = {}
        for side in ['head', 'base']:
            path = ROOT / (side + '-plans-full') / 'scenario/_02_xtests/cases' / (name + '.result')
            sides[side] = [{'plan': plan, 'statement': statement} for plan, statement in
                          re.findall(r'Query plan:\n(.*?)\nQuery stmt:\n([^\n]+)', path.read_text(), re.S)]
        assert len(sides['head']) == len(sides['base']) == (4 if name == 'to_char_order_by' else 1)
        assert sides['head'] == sides['base'], name
        assert all(row['plan'].startswith('sscan\n') for row in sides['head'])
        plans[name] = {'plans': sides, 'byte_equal': True, 'workload': 'complete 114 fixed + complete 444 xtests'}
    (DEST / 'plan-comparison.json').write_text(json.dumps(plans, indent=2) + '\n')
    traces = {}
    for side in ['head', 'base']:
        path = ROOT / (side + '-hp3') / 'gdb.log'
        rows = [json.loads(line.split('[DEBUG-pr7927-heap] ', 1)[1]) for line in path.read_text().splitlines()
                if '[DEBUG-pr7927-heap] ' in line]
        numbers, timestamps = [], []
        for index, row in enumerate(rows):
            if row.get('event') != 'heap_insert_physical' or not row.get('hex64'):
                continue
            data = bytes.fromhex(row['hex64'])
            # Identify the exact observed one-column VARCHAR representations;
            # this is evidence extraction, not a generic record decoder.
            value = None
            kind = None
            if row['length'] == 24 and data[16:21] == bytes.fromhex('040a000001') and data[21] in b'12345':
                value, kind = chr(data[21]), 'to_number_order_by'
            match = re.search(rb'01:0[0-4] 02/(0[1-5])/2000', data[16:])
            if row['length'] == 40 and match:
                value, kind = match[1].decode(), 'to_timestamp_order_by'
            if kind is None:
                continue
            entry = next(previous for previous in reversed(rows[:index])
                if previous.get('event') == 'heap_insert_logical' and previous.get('hex64')
                and previous['hfid'] == row['hfid'] and previous['class_oid'] == row['class_oid']
                and bytes.fromhex(previous['hex64'])[16:] == data[16:])
            event = {'probe_record_ordinal': index + 1, 'value': value, 'logical_entry': entry, 'physical_entry': row}
            (numbers if kind == 'to_number_order_by' else timestamps).append(event)
        numbers, timestamps = numbers[-5:], timestamps[-5:]
        assert [row['value'] for row in numbers] == list('12345')
        assert [row['value'] for row in timestamps] == ['01', '02', '03', '04', '05']
        traces[side] = {'attempt': side + '-hp3', 'to_number_order_by': numbers,
                        'to_timestamp_order_by': timestamps}
    equality = {}
    for name in ['to_number_order_by', 'to_timestamp_order_by']:
        head, base = traces['head'][name], traces['base'][name]
        same_bytes = all(h['physical_entry']['hex64'] == b['physical_entry']['hex64'] for h, b in zip(head, base))
        same_length = all(h['logical_entry']['length'] == b['logical_entry']['length'] ==
                          h['physical_entry']['length'] == b['physical_entry']['length'] for h, b in zip(head, base))
        assert same_bytes and same_length
        equality[name] = {'insertion_value_sequence_equal': True, 'record_lengths_equal': same_length,
                          'complete_physical_record_bytes_equal': same_bytes,
                          'length': head[0]['physical_entry']['length'],
                          'selected_oids_differ': any(h['physical_entry']['res_oid'] != b['physical_entry']['res_oid'] for h, b in zip(head, base))}
    (DEST / 'target-insert-observations.json').write_text(json.dumps({'traces': traces, 'comparison': equality}, indent=2) + '\n')
    print(json.dumps({'original_plans_equal': list(plans), 'target_insert_comparison': equality}))


if __name__ == '__main__':
    main()
