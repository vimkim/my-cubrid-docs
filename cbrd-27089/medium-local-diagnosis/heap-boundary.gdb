set pagination off
set confirm off
handle SIGPIPE nostop noprint pass
handle SIGUSR1 nostop noprint pass
handle SIGTERM nostop noprint pass
python
import gdb, json, os
target_page = int(os.environ['PR7927_DATA_PAGE'])
observed_headers = set()

def oid(v):
    return [int(v['pageid']), int(v['slotid']), int(v['volid'])]

def hfid(v):
    return [int(v['hpgid']), int(v['vfid']['fileid']), int(v['vfid']['volid'])]

class InsertProbe(gdb.Breakpoint):
    def __init__(self, function):
        super().__init__(function, internal=True)
        self.function = function
    def stop(self):
        try:
            context = gdb.parse_and_eval('context').dereference()
            header = int(context['hfid']['hpgid'])
            if self.function == 'heap_insert_physical':
                if int(context['res_oid']['pageid']) not in [target_page, target_page + 1]:
                    return False
                observed_headers.add(header)
            elif header not in observed_headers:
                return False
            record = context['recdes_p'].dereference()
            size, address = int(record['length']), int(record['data'])
            row = {'event': self.function, 'hfid': hfid(context['hfid']),
                   'class_oid': oid(context['class_oid']), 'res_oid': oid(context['res_oid']),
                   'length': size, 'record_type': int(record['type'])}
            if address and size > 0:
                row['hex64'] = gdb.selected_inferior().read_memory(address, min(size, 64)).tobytes().hex()
            print('[DEBUG-pr7927-heap] ' + json.dumps(row), flush=True)
        except gdb.error as error:
            print('[DEBUG-pr7927-heap] ' + json.dumps({'probe_error': str(error)}), flush=True)
        return False

class ReuseProbe(gdb.Breakpoint):
    def __init__(self):
        super().__init__('heap_reuse', internal=True)
    def stop(self):
        heap = gdb.parse_and_eval('hfid').dereference()
        if int(heap['hpgid']) in observed_headers:
            print('[DEBUG-pr7927-heap] ' + json.dumps({'event': 'heap_reuse', 'hfid': hfid(heap),
                'class_oid': oid(gdb.parse_and_eval('class_oid').dereference())}), flush=True)
        return False

InsertProbe('heap_insert_logical')
InsertProbe('heap_insert_physical')
ReuseProbe()
print('[DEBUG-pr7927-heap] ' + json.dumps({'attached': gdb.selected_inferior().pid,
    'filter_data_pages': [target_page, target_page + 1]}), flush=True)
end
continue
