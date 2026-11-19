#!/usr/bin/env python3
"""Is a COMMIT that follows another transaction's log flush durable?

    python3 commit_after_flush_repro.py DBNAME [--cycles 20]

Needs a CUBRID environment (CUBRID, PATH, CUBRID_DATABASES) and an existing database DBNAME whose server is running.
Each cycle builds the state where the commit record of transaction A starts exactly at nxio_lsa:

  1. Session A updates row 1 and does not commit.
  2. Session B updates row 2 and commits. B's commit flushes the log, A's update included, so nxio_lsa ends right
     after B's commit record.
  3. Session A commits. Its commit record is the first record after that flush.
  4. As soon as A's COMMIT returns, the script sends SIGKILL to cub_server, restarts it and reads row 1.

The table has no index, so A's commit appends no record before LOG_COMMIT. A cycle loses the commit when row 1 holds
less than the value A saw acknowledged.
"""

import argparse
import os
import signal
import subprocess
import sys
import tempfile
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


def read_n(db, row):
    for line in csql(db, f"select n from t where id = {row}").splitlines():
        if line.strip().lstrip("-").isdigit():
            return int(line.strip())
    return None


def start_server(db, logdir):
    with (Path(logdir) / "server_start.log").open("ab") as out:
        subprocess.run(["cubrid", "server", "start", db], stdin=subprocess.DEVNULL, stdout=out,
                       stderr=subprocess.STDOUT, start_new_session=True, check=True, timeout=600)


def wait_ready(db, logdir):
    deadline = time.time() + 10
    while server_pid(db) is None and time.time() < deadline:
        time.sleep(0.5)
    if server_pid(db) is None:
        start_server(db, logdir)
    deadline = time.time() + 600
    while time.time() < deadline:
        try:
            csql(db, "select 1")
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("server did not come back")


class Session:
    """One interactive csql session; run() returns once the server answered the statement."""

    def __init__(self, db, name, logdir):
        self.out = Path(logdir) / f"{name}.out"
        self.p = subprocess.Popen(["stdbuf", "-oL", "csql", "-C", "-u", "dba", "--no-auto-commit", "-t", "-N", db],
                                  stdin=subprocess.PIPE, stdout=self.out.open("wb"), stderr=subprocess.STDOUT)
        self.reader = self.out.open("rb")
        self.pos, self.k, self.name = 0, 0, name

    def run(self, sql):
        self.k += 1
        mark = f"mk_{self.name}_{self.k}"
        self.p.stdin.write(f"{sql}\nselect '{mark}';\n".encode())
        self.p.stdin.flush()
        deadline = time.time() + 120
        while time.time() < deadline:
            self.reader.seek(self.pos)
            text = self.reader.read().decode(errors="replace")
            at = text.find(mark)
            if "ERROR" in (text if at < 0 else text[:at]) or self.p.poll() is not None:
                raise RuntimeError(f"{self.name}: {sql}: {text}")
            if at >= 0:
                self.pos += len(text[:at + len(mark)].encode())
                return
            time.sleep(0.0005)
        raise RuntimeError(f"{self.name}: {sql}: timed out")

    def close(self):
        self.reader.close()
        if self.p.poll() is None:
            self.p.kill()
        self.p.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--cycles", type=int, default=20)
    args = ap.parse_args()
    db = args.db
    logdir = tempfile.mkdtemp(prefix="commit_after_flush_")
    csql(db, "drop table if exists t; create table t (id int, n int); insert into t values (1, 0), (2, 0); commit;")
    lost = 0
    for cycle in range(1, args.cycles + 1):
        acked = read_n(db, 1) + 1
        a = Session(db, f"a{cycle}", logdir)
        b = Session(db, f"b{cycle}", logdir)
        try:
            a.run(f"update t set n = {acked} where id = 1;")
            b.run(f"update t set n = n + 1 where id = 2;")
            b.run("commit;")
            a.run("commit;")
            pid = server_pid(db)
            os.kill(pid, signal.SIGKILL)
        finally:
            a.close()
            b.close()
        while server_pid(db) == pid:
            time.sleep(0.05)
        wait_ready(db, logdir)
        got = read_n(db, 1)
        is_lost = got is None or got < acked
        lost += is_lost
        print(f"cycle {cycle}: acknowledged n = {acked}, after restart n = {got}{'  LOST' if is_lost else ''}",
              flush=True)
    print(f"{args.cycles} kills, {lost} lost acknowledged commits", flush=True)
    return 1 if lost else 0


if __name__ == "__main__":
    sys.exit(main())
