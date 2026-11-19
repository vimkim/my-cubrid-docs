#!/usr/bin/env python3
"""Does an acknowledged COMMIT survive kill -9 of cub_server?

    python3 commit_durability_repro.py DBNAME [--cycles 20] [--writers 8]

Needs a CUBRID environment (CUBRID, PATH, CUBRID_DATABASES) and an existing database DBNAME whose server is running.
Each writer owns one row of table c and loops UPDATE c SET n = n + 1, then COMMIT, in its own csql session, waiting
for each statement before it sends the next. A writer records n as acknowledged once the COMMIT returned. After 3 to 12 s the script sends SIGKILL to cub_server, restarts it and
checks that each row holds at least its last acknowledged n.
"""

import argparse
import os
import random
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

BIN = Path(os.environ["CUBRID"]) / "bin"


def server_pid(db):
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            exe = os.readlink(proc / "exe")
            args = (proc / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if exe == str(BIN / "cub_server") and db.encode() in args:
            return int(proc.name)
    return None


def csql(db, sql):
    r = subprocess.run(["csql", "-C", "-u", "dba", "--no-auto-commit", "-t", "-N", "-c", sql, db],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return r.stdout


def read_rows(db):
    rows = {}
    for line in csql(db, "select id, n from c order by id").splitlines():
        p = line.split()
        if len(p) == 2 and p[0].isdigit():
            rows[int(p[0])] = int(p[1])
    return rows


def wait_ready(db):
    deadline = time.time() + 10
    while server_pid(db) is None and time.time() < deadline:
        time.sleep(0.5)
    if server_pid(db) is None:
        subprocess.run(["cubrid", "server", "start", db], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.STDOUT, start_new_session=True, check=True)
    deadline = time.time() + 300
    while time.time() < deadline:
        try:
            csql(db, "select 1")
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("server did not come back")


def writer(db, i, start, acked, stop, logdir):
    out = Path(logdir) / f"w{i}.out"
    p = subprocess.Popen(["stdbuf", "-oL", "csql", "-C", "-u", "dba", "--no-auto-commit", "-t", "-N", db],
                         stdin=subprocess.PIPE, stdout=out.open("wb"), stderr=subprocess.STDOUT)
    pos, n, k = 0, start, 0
    reader = out.open("rb")

    def run(sql):
        nonlocal pos, k
        k += 1
        mark = f"mk_{i}_{k}"
        p.stdin.write(f"{sql}\nselect '{mark}';\n".encode())
        p.stdin.flush()
        while True:
            reader.seek(pos)
            text = reader.read().decode(errors="replace")
            at = text.find(mark)
            if "ERROR" in (text if at < 0 else text[:at]) or p.poll() is not None:
                return False
            if at >= 0:
                pos += len(text[:at + len(mark)].encode())
                return True
            time.sleep(0.001)

    try:
        while not stop.is_set():
            n += 1
            if not run(f"update c set n = {n} where id = {i};") or not run("commit;"):
                return
            acked[i] = n
            p.stdin.write(b"commit;\n")
            p.stdin.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        reader.close()
        if p.poll() is None:
            p.kill()
            p.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--cycles", type=int, default=20)
    ap.add_argument("--writers", type=int, default=8)
    args = ap.parse_args()
    db, W = args.db, args.writers
    rows = ", ".join(f"({i}, 0)" for i in range(W))
    csql(db, f"drop table if exists c; create table c (id int primary key, n int); insert into c values {rows}; commit;")
    logdir = tempfile.mkdtemp(prefix="commit_repro_")
    lost_total = 0
    for cycle in range(1, args.cycles + 1):
        base = read_rows(db)
        acked = dict(base)
        stop = threading.Event()
        ths = [threading.Thread(target=writer, args=(db, i, base[i], acked, stop, logdir), daemon=True)
               for i in range(W)]
        for t in ths:
            t.start()
        time.sleep(random.uniform(3, 12))
        pid = server_pid(db)
        os.kill(pid, signal.SIGKILL)
        stop.set()
        for t in ths:
            t.join(60)
        while server_pid(db) == pid:
            time.sleep(0.1)
        wait_ready(db)
        got = read_rows(db)
        lost = [(i, got.get(i), acked[i]) for i in range(W) if got.get(i) is None or got[i] < acked[i]]
        commits = sum(acked[i] - base[i] for i in range(W))
        print(f"cycle {cycle}: {commits} acknowledged commits, lost (row, after restart, acknowledged): {lost}",
              flush=True)
        lost_total += len(lost)
    print(f"{args.cycles} kills, {lost_total} lost acknowledged commits", flush=True)
    return 1 if lost_total else 0


if __name__ == "__main__":
    sys.exit(main())
