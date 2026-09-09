# Diagnostic counts only; never use debugger-wrapped durations as timing evidence.
set pagination off
set confirm off
set breakpoint pending on
python
import gdb, json, collections
from pathlib import Path
active = False
counts = collections.Counter()
errors = []
had_errors = False
points = []
live = {}
def in_force():
    frame = gdb.newest_frame()
    while frame:
        if frame.name() and 'locator_attribute_info_force' in frame.name(): return True
        frame = frame.older()
    return False
def acquire(ptr, size, category):
    if not int(ptr): return
    live[int(ptr)] = (size, category)
    counts[category + '_acquired_bytes'] += size
    counts['tracked_temporary_peak_bytes'] = max(counts['tracked_temporary_peak_bytes'], sum(x[0] for x in live.values()))
def release(ptr):
    if int(ptr) in live:
        size, category = live.pop(int(ptr))
        counts[category + '_released_bytes'] += size
def value(name):
    return gdb.parse_and_eval(name)
def fail(exc):
    errors.append(str(exc))
class Finish(gdb.FinishBreakpoint):
    def __init__(self, callback):
        super().__init__(gdb.newest_frame(), internal=True)
        self.callback = callback
    def stop(self):
        try:
            self.callback(self.return_value)
        except Exception as exc:
            fail(exc)
        return False
class Count(gdb.Breakpoint):
    def __init__(self, name, key, callback=None):
        super().__init__(name, internal=True)
        self.key, self.callback = key, callback
        self.enabled = False
        points.append(self)
    def stop(self):
        counts[self.key] += 1
        if self.callback:
            try:
                self.callback()
            except Exception as exc:
                fail(exc)
        return False
def transform():
    probe = int(value("would_demote_oos")) != 0
    counts["probe_transforms" if probe else "real_transforms"] += 1
    rec = value("new_recdes")
    def done(ret):
        if int(ret) == 1:
            counts["probe_row_serialized_bytes" if probe else "real_row_serialized_bytes"] += int(rec.dereference()["m_recdes"]["length"])
    Finish(done)
def payload():
    rec = value("recdes")
    def done(ret):
        if int(ret) == 1:
            counts["oos_payload_serialized_bytes"] += int(rec.dereference()["length"])
            counts["oos_payload_buffer_bytes"] += int(rec.dereference()["area_size"])
            acquire(rec.dereference()['data'], int(rec.dereference()['area_size']), 'payload_malloc')
    Finish(done)
def copyarea():
    scoped = in_force()
    def done(ret):
        if int(ret):
            counts["copyarea_leased_bytes"] += int(ret.dereference()["length"])
            if scoped: acquire(ret, int(ret.dereference()['length']), 'routing_copyarea_lease')
    Finish(done)
def growth():
    size = int(value("required_size"))
    area = int(value("this").dereference()["m_recdes"]["area_size"])
    if size > area:
        counts["record_buffer_growth_requests"] += 1
        counts["record_buffer_requested_bytes"] += size
        counts["record_buffer_max_request"] = max(counts["record_buffer_max_request"], size)
        rec = value('this')
        Finish(lambda ret: acquire(rec.dereference()['m_recdes']['data'], size, 'record_buffer_malloc'))
def private_alloc():
    if in_force():
        size = int(value('size'))
        Finish(lambda ret: acquire(ret, size, 'private_allocation'))
Count("heap_attrinfo_transform_to_disk_internal", "full_row_transforms", transform)
Count("heap_attrinfo_transform_columns_to_disk", "column_writer_attempts")
Count("heap_attrinfo_dbvalue_to_recdes", "oos_payload_serializations", payload)
Count("locator_allocate_copy_area_by_length", "copyarea_leases", copyarea)
Count("record_descriptor::resize_buffer", "resize_calls", growth)
Count("partition_prune_insert", "record_insert_routes")
Count("partition_prune_update", "record_update_routes")
Count("partition_prune_insert_by_attrinfo", "attribute_insert_routes")
Count("partition_prune_update_by_attrinfo", "attribute_update_routes")
Count("heap_attrinfo_get_effective_key", "effective_key_preparations")
Count("oos_insert_many", "oos_insert_many_calls")
Count('locator_free_copy_area', 'copyarea_returns', lambda: release(value('copyarea')))
Count('db_private_alloc_release', 'private_alloc_calls', private_alloc)
Count('db_private_free_release', 'private_free_calls', lambda: release(value('ptr')))
# x86-64 SysV ABI: free's first argument; avoids depending on distribution libc argument names.
Count('__libc_free', 'libc_free_calls', lambda: release(value('$rdi')))
source = Path(gdb.current_progspace().filename).resolve().parents[2]
for rel, anchor, expression, key in [
    ('src/transaction/locator_sr.c', 'std::memcpy (copyarea->mem, allocated_data, build_record.get_size ());',
     'build_record.m_recdes.length', 'grown_record_copy_bytes'),
    ('src/storage/heap_file.c', 'error = pr_type->data_writeval (&buf, &prepared);',
     'buf.endptr - buf.buffer', 'effective_key_codec_bytes')]:
    path = source / rel
    matches = [i for i, line in enumerate(path.read_text().splitlines(), 1) if anchor in line]
    if matches:
        if len(matches) != 1: raise RuntimeError('ambiguous measurement anchor')
        Count(str(path) + ':' + str(matches[0]), key + '_events',
              lambda e=expression, k=key: counts.update({k:int(value(e))}))
class Begin(gdb.Breakpoint):
    def stop(self):
        global counts, errors, live
        counts, errors = collections.Counter(), []
        live = {}
        for point in points: point.enabled = True
        return False
class End(gdb.Breakpoint):
    def stop(self):
        global had_errors
        for point in points: point.enabled = False
        counts['tracked_bytes_outstanding_at_end'] = sum(x[0] for x in live.values())
        if not counts['full_row_transforms']: errors.append('no full-row transform observed')
        had_errors = had_errors or bool(errors)
        print("PR7600_DIAGNOSTIC " + json.dumps({"counts":dict(counts), "errors":errors}, sort_keys=True))
        return False
Begin("pr7600_measure_begin", internal=True)
End("pr7600_measure_end", internal=True)
end
run
python
if had_errors: gdb.execute('quit 1')
end
if $_exitcode != 0
  quit 1
end
quit 0
