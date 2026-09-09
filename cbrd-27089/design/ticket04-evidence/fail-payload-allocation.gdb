# Fail the OOS payload malloc instead of the later publication allocation at the two OOM scenarios.
# The ordinary, unwrapped test independently covers publication-vector allocation failure.
set pagination off
set confirm off
set breakpoint pending on
python
import gdb
armed = False
injected = 0
class Arm(gdb.Breakpoint):
    def stop(self):
        global armed
        armed = True
        return False
class Allocation(gdb.Breakpoint):
    def stop(self):
        global armed, injected
        if not armed: return False
        frame = gdb.newest_frame()
        while frame:
            if frame.name() and 'heap_attrinfo_dbvalue_to_recdes' in frame.name():
                armed = False
                injected += 1
                print('TICKET04_PAYLOAD_MALLOC_FAILURE', injected)
                gdb.execute('return (void *) 0', to_string=True)
                break
            frame = frame.older()
        return False
Arm('oos_test_throw_bad_alloc_on_next_oid_publication', internal=True)
Allocation('__libc_malloc', internal=True)
end
run
python
if injected != 2: gdb.execute('quit 1')
end
if $_exitcode != 0
  quit 1
end
quit 0

