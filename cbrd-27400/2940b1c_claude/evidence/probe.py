# GDB Python probe for bug_bts_4633: widen the window between the two loads of
# log_Gl.hdr.append_lsa in log_get_undo_record (optdebug build):
#   +45: mov    (%rax),%rcx        <- word 1: page id taken from low 48 bits
#   +48: movzwl 0x6(%rax),%esi     <- word 2: offset taken from bytes 6..7
#   +117: lea ...,%rcx             <- unique entry of the assert-failure branch
# No database content is modified. The process only ever pauses while its own
# thread is stopped at +48, exactly as the OS scheduler could preempt it there.
import gdb, os, time

PROBE_DIR = os.environ.get("PROBE_DIR", ".")
LOG = open(os.path.join(PROBE_DIR, "probe-events.log"), "a", buffering=1)
MASK48 = 0xffffffffffff
MAX_WAIT_S = float(os.environ.get("PROBE_MAX_WAIT_S", "0.2"))
MODE = os.environ.get("PROBE_MODE", "pause")  # pause | count
POLL_S = 0.0002

def log(msg):
    LOG.write("%.6f %s\n" % (time.time(), msg))

def lsa(word):
    pid = word & MASK48
    if pid & (1 << 47):
        pid -= 1 << 48
    off = (word >> 48) & 0xffff
    if off & 0x8000:
        off -= 0x10000
    return (pid, off)

def read_u64(addr):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(addr, 8)), "little")

ADDR_APPEND = int(gdb.parse_and_eval("(unsigned long)&log_Gl.hdr.append_lsa"))
ADDR_PRIOR = int(gdb.parse_and_eval("(unsigned long)&log_Gl.prior_info.prior_lsa"))
log("probe start: mode=%s &append_lsa=0x%x &prior_lsa=0x%x max_wait=%.3fs" % (MODE, ADDR_APPEND, ADDR_PRIOR, MAX_WAIT_S))

class PauseBetweenLoads(gdb.Breakpoint):
    def __init__(self):
        super().__init__("*log_get_undo_record+48", gdb.BP_BREAKPOINT)
        self.hits = self.same_page = self.candidates = self.rollovers = self.would_fail = 0

    def stop(self):
        self.hits += 1
        try:
            f = gdb.selected_frame()
            rcx = int(f.read_register("rcx").cast(gdb.lookup_type("unsigned long")))
            rbp = int(f.read_register("rbp").cast(gdb.lookup_type("unsigned long")))
            proc = read_u64(rbp - 0x4048)
            rpid, roff = lsa(rcx)
            ppid, poff = lsa(proc)
            if self.hits % (200 if MODE == "count" else 2000) == 0:
                log("[STATS] hits=%d same_page=%d candidates=%d rollovers=%d would_fail=%d"
                    % (self.hits, self.same_page, self.candidates, self.rollovers, self.would_fail))
            if rpid != ppid:
                return False
            self.same_page += 1
            prpid, proff = lsa(read_u64(ADDR_PRIOR))
            if prpid <= rpid:
                return False          # next prior-list flush would not roll the page
            self.candidates += 1
            if MODE == "count":
                return False          # unforced: observe only, never widen the window
            lwp = gdb.selected_thread().ptid[1]
            t0 = time.monotonic()
            while True:
                cpid, coff = lsa(read_u64(ADDR_APPEND))
                if cpid > rpid:
                    self.rollovers += 1
                    verdict = "ASSERT-WILL-FAIL" if poff >= coff else "survives"
                    if poff >= coff:
                        self.would_fail += 1
                    log("[ROLLOVER-IN-WINDOW] lwp=%d word1(first load)=(%d,%d) process_lsa=(%d,%d) "
                        "prior_lsa@stop=(%d,%d) append_lsa now=(%d,%d) waited_ms=%.2f -> second load reads offset %d : %s"
                        % (lwp, rpid, roff, ppid, poff, prpid, proff, cpid, coff, (time.monotonic() - t0) * 1000, coff, verdict))
                    break
                if time.monotonic() - t0 > MAX_WAIT_S:
                    log("[NO-ROLLOVER] lwp=%d word1=(%d,%d) process_lsa=(%d,%d) prior_lsa@stop=(%d,%d) append now=(%d,%d)"
                        % (lwp, rpid, roff, ppid, poff, prpid, proff, cpid, coff))
                    break
                time.sleep(POLL_S)
        except Exception as e:
            log("[PROBE-ERROR] %r" % (e,))
        return False

TERMINAL = {"hit": False, "thread": None, "which": None}

class AssertBranch(gdb.Breakpoint):
    """+117 is reached only when LSA_LT(process_lsa, oldest_prior_lsa) is false."""
    def __init__(self):
        super().__init__("*log_get_undo_record+117", gdb.BP_BREAKPOINT)
    def stop(self):
        TERMINAL.update(hit=True, thread=gdb.selected_thread(), which="assert-branch(+117)")
        log("[TERMINAL] assert branch reached on lwp=%d" % gdb.selected_thread().ptid[1])
        return True

class AnyAssert(gdb.Breakpoint):
    def __init__(self):
        super().__init__("__assert_fail", gdb.BP_BREAKPOINT)
    def stop(self):
        if not TERMINAL["hit"]:
            TERMINAL.update(hit=True, thread=gdb.selected_thread(), which="__assert_fail")
        log("[TERMINAL] __assert_fail reached on lwp=%d" % gdb.selected_thread().ptid[1])
        return True

class CountRollover(gdb.Breakpoint):
    def __init__(self):
        super().__init__("logpb_next_append_page", gdb.BP_BREAKPOINT)
        self.count = 0
        self.t0 = time.monotonic()
    def stop(self):
        self.count += 1
        if self.count % 500 == 0:
            log("[ROLLOVERS] count=%d elapsed_s=%.1f" % (self.count, time.monotonic() - self.t0))
        return False

rollover_bp = CountRollover() if MODE == "count" else None
pause_bp = PauseBetweenLoads()
assert_branch_bp = AssertBranch()
any_assert_bp = AnyAssert()
T_START = time.monotonic()
log("breakpoints set; resuming all threads")

spurious = 0
while not TERMINAL["hit"]:
    try:
        gdb.execute("continue -a")
    except gdb.error as e:
        log("[CONTINUE-ENDED] %r" % (e,))
        break
    if TERMINAL["hit"]:
        break
    spurious += 1
    try:
        why = gdb.execute("info program", to_string=True).strip().replace("\n", " | ")
    except gdb.error as e:
        why = repr(e)
    log("[SPURIOUS-STOP #%d] %s" % (spurious, why))
    if spurious > 500:
        log("[GIVING-UP] too many non-terminal stops")
        break

def dump():
    try:
        if TERMINAL["thread"] is not None:
            TERMINAL["thread"].switch()
            log("[TERMINAL-KIND] %s" % TERMINAL["which"])
        f = gdb.selected_frame()
        pc = int(f.pc())
        log("[STOP] thread=%s pc=0x%x %s" % (gdb.selected_thread().ptid, pc, f.name()))
        if f.name() and "log_get_undo_record" in f.name():
            rcx = int(f.read_register("rcx").cast(gdb.lookup_type("unsigned long")))
            esi = int(f.read_register("rsi").cast(gdb.lookup_type("unsigned long"))) & 0xffff
            rbp = int(f.read_register("rbp").cast(gdb.lookup_type("unsigned long")))
            proc = read_u64(rbp - 0x4048)
            # +83 executed 'xor -0x4048(%rbp),%rcx' on the equal-or-greater path, so undo it to recover word1
            word1 = rcx ^ proc
            log("[ASSERT-INPUTS] rcx@+117=0x%016x (= word1 XOR process_lsa) ; word1(first load)=0x%016x -> %s ; "
                "second load offset(esi)=%d ; process_lsa=0x%016x -> %s ; coherent append_lsa now=%s ; prior_lsa now=%s"
                % (rcx, word1, lsa(word1), esi, proc, lsa(proc), lsa(read_u64(ADDR_APPEND)), lsa(read_u64(ADDR_PRIOR))))
            log("[ASSERT-INPUTS] effective compared value = (pageid from word1, offset from second load) = (%d,%d) ; "
                "assert needs process_lsa %s < that" % (lsa(word1)[0], esi, lsa(proc)))
        log("[BT]\n" + gdb.execute("bt 16", to_string=True))
        log("[REGS]\n" + gdb.execute("info registers rax rcx rdx rsi rbp", to_string=True))
        log("[GLOBALS]\n" + gdb.execute("p log_Gl.hdr.append_lsa", to_string=True)
            + gdb.execute("p log_Gl.prior_info.prior_lsa", to_string=True)
            + gdb.execute("p log_Gl.append.prev_lsa", to_string=True))
    except Exception as e:
        log("[DUMP-ERROR] %r" % (e,))

dump()
log("[FINAL-STATS] mode=%s hits=%d same_page=%d candidates=%d rollovers_in_window=%d would_fail=%d rollover_bp_count=%s elapsed_s=%.1f"
    % (MODE, pause_bp.hits, pause_bp.same_page, pause_bp.candidates, pause_bp.rollovers, pause_bp.would_fail,
       rollover_bp.count if rollover_bp else "n/a", time.monotonic() - T_START))
try:
    gdb.execute("detach")   # let the server abort and dump core naturally
    log("detached")
except gdb.error as e:
    log("[DETACH] %r" % (e,))
LOG.close()
