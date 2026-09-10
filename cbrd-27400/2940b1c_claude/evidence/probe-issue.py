import gdb, time
MASK = 0xffffffffffff
def lsa(w):
    p = w & MASK
    if p & (1 << 47): p -= 1 << 48
    o = (w >> 48) & 0xffff
    if o & 0x8000: o -= 0x10000
    return (p, o)
def u64(addr):
    return int.from_bytes(bytes(gdb.selected_inferior().read_memory(addr, 8)), "little")
def reg(f, name):
    return int(f.read_register(name).cast(gdb.lookup_type("unsigned long")))
def process_lsa_word():                           # 스필된 인자 process_lsa 를 DWARF 위치로 읽는다
    return int(gdb.parse_and_eval("*(unsigned long *) &process_lsa"))
APPEND = int(gdb.parse_and_eval("(unsigned long)&log_Gl.hdr.append_lsa"))
PRIOR = int(gdb.parse_and_eval("(unsigned long)&log_Gl.prior_info.prior_lsa"))
HIT = []
class Pause(gdb.Breakpoint):                      # LOAD 1 과 LOAD 2 사이
    def stop(self):
        word1 = reg(gdb.selected_frame(), "rcx")
        proc = process_lsa_word()
        if lsa(word1)[0] != lsa(proc)[0] or lsa(u64(PRIOR))[0] <= lsa(word1)[0]:
            return False                          # 이전 버전이 현재 페이지가 아니거나, 다음 flush 가 페이지를 넘기지 않음
        t0 = time.monotonic()
        while time.monotonic() - t0 < 0.2 and lsa(u64(APPEND))[0] <= lsa(word1)[0]:
            time.sleep(0.0002)                    # 다른 스레드가 prior list 를 flush 해 페이지를 넘길 때까지
        print("paused: word1=%s process_lsa=%s append_now=%s" % (lsa(word1), lsa(proc), lsa(u64(APPEND))))
        return False
class Stop(gdb.Breakpoint):
    def stop(self):
        HIT.append(gdb.selected_thread()); return True
Pause("*log_get_undo_record+48"); Stop("*log_get_undo_record+117"); Stop("__assert_fail")
while not HIT:
    gdb.execute("continue -a")                    # attach 직후 idle 스레드의 가짜 stop 은 그냥 재개
HIT[0].switch()
f = gdb.selected_frame()
if f.name() and "log_get_undo_record" in f.name():   # +117 에서 rcx 는 이미 word1 XOR process_lsa 다
    proc = process_lsa_word()
    print("word1=%s load2_offset=%d process_lsa=%s append_now=%s"
          % (lsa(reg(f, "rcx") ^ proc), reg(f, "rsi") & 0xffff, lsa(proc), lsa(u64(APPEND))))
gdb.execute("bt 8")                               # 다른 assert 였다면 스택만 남긴다
gdb.execute("detach")                             # 서버는 그대로 abort 하고 core 를 남긴다
