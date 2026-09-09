# Ticket04: force a real column-buffer retry after demoted BLOB preparation.
set pagination off
set confirm off
set breakpoint pending on
python
import gdb, json, os, hashlib
from pathlib import Path
scope = None
injected = False
verified = False
original_inventory = None
abort_checks = 0
physical_deletes = []
lob_root = Path(os.environ['CUBRID_DATABASES']) / 'unittestdb/lob'
def inventory():
    return {str(p.relative_to(lob_root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in lob_root.rglob('*') if p.is_file()}
class Finish(gdb.FinishBreakpoint):
    def stop(self):
        global scope, verified
        if scope and scope['injected']:
            print('TICKET04_LOB_RETRY ' + json.dumps(scope))
            if scope['copies'] != 2 or scope['deletes'] != 2 or scope['column_attempts'] != 2 or int(self.return_value) != 1:
                gdb.execute('quit 1')
            verified = True
        scope = None
        return False
class Transform(gdb.Breakpoint):
    def stop(self):
        global scope
        cache = gdb.parse_and_eval('attr_info')
        if int(gdb.parse_and_eval('old_recdes')) and int(cache.dereference()['num_values']) == 4:
            scope = dict(copies=0, deletes=0, column_attempts=0, injected=False)
            Finish(gdb.newest_frame(), internal=True)
        return False
class Copy(gdb.Breakpoint):
    def stop(self):
        if scope is not None: scope['copies'] += 1
        return False
class Delete(gdb.Breakpoint):
    def stop(self):
        if scope is not None: scope['deletes'] += 1
        return False
class PhysicalDelete(gdb.Breakpoint):
    def stop(self):
        physical_deletes.append(gdb.parse_and_eval('uri').string())
        return False
class TransactionFinish(gdb.FinishBreakpoint):
    def __init__(self, abort):
        super().__init__(gdb.newest_frame(), internal=True)
        self.abort = abort
    def stop(self):
        global original_inventory, abort_checks, physical_deletes
        now = inventory()
        if self.abort and original_inventory is not None:
            abort_checks += 1
            print('TICKET04_LOB_ABORT ' + json.dumps(dict(inventory=now, physical_deletes=physical_deletes)))
            if int(self.return_value) != 0 or now != original_inventory:
                gdb.execute('quit 1')
            if len(set(physical_deletes)) != len(physical_deletes):
                print('Duplicate physical deletion in one transaction interval')
                gdb.execute('quit 1')
        elif not self.abort and original_inventory is None and now:
            original_inventory = now
            print('TICKET04_LOB_SEED ' + json.dumps(now))
            if len(now) != 4: gdb.execute('quit 1')
        physical_deletes = []
        return False
class Transaction(gdb.Breakpoint):
    def __init__(self, name, abort):
        super().__init__(name, internal=True)
        self.abort = abort
    def stop(self):
        TransactionFinish(self.abort)
        return False
class Columns(gdb.Breakpoint):
    def stop(self):
        if scope is not None: scope['column_attempts'] += 1
        return False
class Shrink(gdb.Breakpoint):
    def stop(self):
        global injected
        if scope is not None and not injected:
            gdb.execute('set inline_size_after_oos = header_size + 64', to_string=True)
            scope['injected'] = injected = True
        return False
Transform('heap_attrinfo_transform_to_disk_internal', internal=True)
Copy('db_elo_copy_with_prefix', internal=True)
Delete('db_elo_delete', internal=True)
PhysicalDelete('es_delete_file', internal=True)
Transaction('db_abort_transaction', True)
Transaction('db_commit_transaction', False)
Columns('heap_attrinfo_transform_columns_to_disk', internal=True)
Shrink('heap_file.c:13557', internal=True)
end
run
python
if not verified or abort_checks != 6 or inventory(): gdb.execute('quit 1')
print('TICKET04_LOB_LIFETIME PASS: six abort inventories restored; teardown leaves no external files')
end
if $_exitcode != 0
  quit 1
end
quit 0
