#!/usr/bin/env python3
"""Does a prepared 2PC transaction stay committed after an attach, an acknowledged COMMIT and a kill -9?

    python3 twopc_attach_repro.py DBNAME TWOPC_BINARY [--cycles 5]

Scenario from the CBRD-28065 comment of 2026-11-18. Each cycle:
  1. Client 1 starts a 2PC transaction, updates row 7 of table r and prepares it, then stays connected.
  2. kill -9 cub_server and restart it; recovery keeps the transaction prepared.
  3. Client 2 attaches to the transaction and commits it. The script waits for the acknowledgement.
  4. kill -9 cub_server and restart it.
The cycle loses the commit when the transaction is listed as prepared again after step 4.
"""

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commit_after_flush_repro import csql, server_pid, wait_ready  # noqa: E402


def start_client(twopc, args, out):
    p = subprocess.Popen([twopc, *args], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=out, text=True)
    line = p.stdout.readline().strip()
    if not line:
        p.wait()
        raise RuntimeError(f"twopc {args} printed nothing, rc={p.returncode}")
    return p, line


def kill_server_and_restart(db, logdir):
    pid = server_pid(db)
    os.kill(pid, signal.SIGKILL)
    while server_pid(db) == pid:
        time.sleep(0.05)
    wait_ready(db, logdir)


def prepared(twopc, db):
    r = subprocess.run([twopc, "list", db], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(r.stdout + r.stderr)
    return [int(line.split()[1]) for line in r.stdout.splitlines() if line.startswith("prepared ")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("twopc")
    ap.add_argument("--cycles", type=int, default=5)
    args = ap.parse_args()
    db, twopc = args.db, args.twopc
    logdir = tempfile.mkdtemp(prefix="twopc_attach_")
    err = (Path(logdir) / "clients.err").open("w")
    lost = 0
    for cycle in range(1, args.cycles + 1):
        csql(db, "drop table if exists r; create table r (id int primary key, v int); insert into r values (7, 0); "
                 "commit;")
        c1, line = start_client(twopc, ["prepare", db], err)
        gtrid = int(line.split()[1])
        kill_server_and_restart(db, logdir)
        c1.kill()
        c1.wait()
        before = prepared(twopc, db)
        if gtrid not in before:
            raise RuntimeError(f"cycle {cycle}: gtrid {gtrid} not prepared after the first restart: {before}")
        c2, line = start_client(twopc, ["attach-commit", db, str(gtrid)], err)
        assert line == f"committed {gtrid}", line
        kill_server_and_restart(db, logdir)
        c2.kill()
        c2.wait()
        after = prepared(twopc, db)
        is_lost = gtrid in after
        lost += is_lost
        print(f"cycle {cycle}: gtrid {gtrid} commit acknowledged, prepared after restart: {after}"
              f"{'  LOST' if is_lost else ''}", flush=True)
        if is_lost:
            c3, line = start_client(twopc, ["attach-commit", db, str(gtrid)], err)
            c3.kill()
            c3.wait()
    print(f"{args.cycles} cycles, {lost} acknowledged 2PC commits came back prepared", flush=True)
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
