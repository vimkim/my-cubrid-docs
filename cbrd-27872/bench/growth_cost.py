#!/usr/bin/env python3
"""CBRD-27872 / ADR-0010 decision 6: OOS growth cost, before vs after.

One persistent database per build. Rounds alternate the builds; only one server
runs at a time. Every measured INSERT runs inside one csql session whose
statement time comes from csql's own timer, and whose data page fetches come
from SHOW EXEC STATISTICS, so a full-file lap shows up as ~file-size fetches.

Results: OUT/results.csv with columns label,sha,round,item,iter,metric,value.
"""
import argparse
import csv
import json
import os
import pathlib
import re
import subprocess
import sys
import time

STMT_TIME = re.compile(r"row(?:s)? affected\. \((\d+\.\d+) sec\)")
STAT = re.compile(r"'(data_page_\w+)'\s+(\d+)")
OOS_FIELD = re.compile(r"^\s*(Oos_\w+)\s*:\s*(\S+)", re.M)

CFG = dict(
    t_rows=20000, t_bytes=10000,   # one chunk per page: every new value needs a new page
    u_rows=40000, u_bytes=7000,    # two chunks per page: deleting one leaves the page in use
    c_rows=2000, c_bytes=7000,     # churn table for the file-size check
    buffer="256M",
)


def value_expr(key_sql, nbytes):
    return f"CAST(REPEAT(LPAD(HEX({key_sql}), 8, '0'), {nbytes // 4}) AS BIT VARYING)"


class Build:
    def __init__(self, label, install, sha, root, port, db="gdb"):
        self.label, self.db, self.port = label, db, port
        self.install = pathlib.Path(install).resolve()
        self.root = pathlib.Path(root)
        self.logs = self.root / "logs"
        self.sha = sha
        self.env = dict(os.environ)
        self.env.update(
            CUBRID=str(self.install),
            PATH=f"{self.install}/bin:{os.environ['PATH']}",
            LD_LIBRARY_PATH=f"{self.install}/lib",
            CUBRID_DATABASES=str(self.root),
            CUBRID_CONF_FILE=str(self.root / "cubrid.conf"),
            CUBRID_TMP=str(self.root / "tmp"),
        )
        self.seq = len(list(self.logs.glob("*"))) if self.logs.exists() else 0
        self.state_path = self.root / "state.json"

    def state(self):
        if self.state_path.exists():
            return json.loads(self.state_path.read_text())
        return {"next_key": 1_000_000, "t_del": 0, "u_del": 0, "rounds": 0}

    def save(self, st):
        self.state_path.write_text(json.dumps(st))

    def take(self, field, step=1):
        st = self.state()
        st[field] += step
        self.save(st)
        return st[field]

    def _log(self, name):
        self.seq += 1
        return self.logs / f"{self.seq:05d}-{name}"

    def run(self, args, name, timeout=600, check=True):
        path = self._log(name)
        with open(path, "wb") as out:
            p = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                               env=self.env, cwd=self.root, timeout=timeout)
        text = path.read_text(errors="replace")
        if check and p.returncode != 0:
            raise RuntimeError(f"{self.label}: {' '.join(args[:3])} rc={p.returncode}, see {path}")
        return text

    def csql(self, sql, name, autocommit=True, timeout=1800):
        script = self._log(name + ".sql")
        script.write_text(sql)
        args = ["csql", "-C", "-u", "dba", "-i", str(script), self.db]
        if not autocommit:
            args.insert(2, "--no-auto-commit")
        return self.run(args, name + ".out", timeout=timeout)

    def daemon(self, args, name, timeout=300):
        # CBRD-27443: daemons keep inherited pipes open, so capture to regular files in a new session.
        path = self._log(name)
        with open(path, "wb") as out:
            p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                 env=self.env, cwd=self.root, close_fds=True, start_new_session=True)
            rc = p.wait(timeout=timeout)
        if rc != 0:
            raise RuntimeError(f"{self.label}: {' '.join(args)} rc={rc}, see {path}")

    def start(self):
        self.daemon(["cubrid", "server", "start", self.db], "server-start")

    def stop(self):
        self.daemon(["cubrid", "server", "stop", self.db], "server-stop")
        self.daemon(["cubrid", "service", "stop"], "service-stop")

    def oos(self, table):
        out = self.run(["csql", "-C", "-u", "dba", "-l", "-c", f"SHOW HEAP OOS OF {table}", self.db], f"oos-{table}")
        return {k: int(v) for k, v in OOS_FIELD.findall(out) if v.lstrip("-").isdigit()}

    def oos_sectors(self):
        """Server must be down: diagdb runs standalone. Returns {table: reserved sectors of its OOS file}."""
        dump = self._log("diagdb.txt")
        self.run(["cubrid", "diagdb", "-d", "1", "-o", str(dump), self.db], "diagdb")
        text = dump.read_text(errors="replace")
        res = {}
        for block in text.split(" Dumping file ")[1:]:
            m = re.search(r"sector: total = (\d+)", block)
            t = re.search(r"type = (\w+)", block)
            c = re.search(r"CLASS_OID:[^(]*\(dba\.(\w+)\), OOS for HFID", block)
            if m and t and t.group(1) == "OUT_OF_LINE_OVERFLOW_STORAGE" and c:
                res[c.group(1)] = int(m.group(1))
        dump.unlink()
        return res

    def create(self):
        for d in (self.root, self.logs, self.root / "tmp"):
            d.mkdir(parents=True, exist_ok=True)
        (self.root / "cubrid.conf").write_text(
            "[service]\nservice=server\n[common]\n"
            f"cubrid_port_id={self.port}\ndata_buffer_size={CFG['buffer']}\n"
            "log_buffer_size=64M\nerror_log_level=error\n")
        (self.root / "databases.txt").touch()
        self.run(["cubrid", "createdb", "--db-volume-size=2G", "--log-volume-size=1G", "-F", str(self.root),
                  self.db, "en_US.utf8"], "createdb")
        self.start()
        self.csql(
            "CREATE TABLE nums (id INT);\n"
            "INSERT INTO nums SELECT ROWNUM FROM db_class a, db_class b, db_class c WHERE ROWNUM <= 60000;\n"
            "CREATE TABLE f (id INT, s VARCHAR(2000));\n"
            "CREATE TABLE t (id INT PRIMARY KEY, v BIT VARYING);\n"
            "CREATE TABLE u (id INT PRIMARY KEY, v BIT VARYING);\n"
            "CREATE TABLE p (id INT PRIMARY KEY, v BIT VARYING);\n"
            f"INSERT INTO p VALUES (1, {value_expr('1', CFG['t_bytes'])});\n", "schema")
        for table, rows, nbytes in (("t", CFG["t_rows"], CFG["t_bytes"]), ("u", CFG["u_rows"], CFG["u_bytes"])):
            for lo in range(0, rows, 5000):
                self.csql(f"INSERT INTO {table} SELECT id, {value_expr('id', nbytes)} FROM nums "
                          f"WHERE id > {lo} AND id <= {min(lo + 5000, rows)};\n", f"load-{table}-{lo}")
        info = {tb: self.oos(tb) for tb in ("t", "u", "p")}
        self.stop()
        return info


def parse_session(out):
    """Return [(stmt_sec, {stat: value})] for each INSERT followed by SHOW EXEC STATISTICS."""
    times = [float(x) for x in STMT_TIME.findall(out)]
    pairs = STAT.findall(out)
    stats = [dict((k, int(v)) for k, v in pairs[i:i + 4]) for i in range(0, len(pairs), 4)]
    return times, stats


class Runner:
    def __init__(self, out):
        self.out = pathlib.Path(out)
        self.csv_path = self.out / "results.csv"
        new = not self.csv_path.exists()
        self.fh = open(self.csv_path, "a", newline="")
        self.conc_iters, self.workers, self.plain_n = 0, 8, 0
        self.w = csv.writer(self.fh)
        if new:
            self.w.writerow(["label", "sha", "round", "item", "iter", "metric", "value"])

    def emit(self, b, rnd, item, it, metric, value):
        self.w.writerow([b.label, b.sha, rnd, item, it, metric, value])
        self.fh.flush()

    def key(self, b):
        return b.take("next_key")

    def insert_session(self, b, table, nbytes, name, n=2):
        """Warm the session, then n INSERTs that each need a new OOS page, each followed by stats."""
        keys = [self.key(b) for _ in range(n)]
        sql = "SET @collect_exec_stats = 1;\n" f"SELECT id FROM {table} WHERE id = 1;\n"
        for k in keys:
            sql += f"INSERT INTO {table} SELECT {k}, {value_expr(str(k), nbytes)} FROM db_root;\nSHOW EXEC STATISTICS;\n"
        out = b.csql(sql, name)
        times, stats = parse_session(out)
        # the warm-up SELECT prints "1 row selected", not "affected", so times are the INSERTs only
        if len(times) != n or len(stats) != n:
            raise RuntimeError(f"{b.label}: parsed {len(times)} times / {len(stats)} stats in {name}")
        return times, stats

    def drain(self, b):
        """Push the log until vacuum has removed the probe's dead chunk, then a margin for parallel workers."""
        for i in range(600):
            if b.oos("p").get("Oos_num_recs") == 1:
                time.sleep(0.5)
                return i
            b.run(["csql", "-C", "-u", "dba", "-c",
                   "INSERT INTO f SELECT id, REPEAT('f', 1500) FROM nums WHERE id <= 200", b.db], "filler")
            time.sleep(0.1)
        raise RuntimeError(f"{b.label}: vacuum did not drain")

    def delete_then_insert(self, b, rnd, item, it, table, del_id, nbytes):
        b.csql(f"DELETE FROM {table} WHERE id = {del_id};\n"
               f"UPDATE p SET v = {value_expr(str(self.key(b)), CFG['t_bytes'])} WHERE id = 1;\nCOMMIT;\n",
               f"{item}-delete", autocommit=False)
        fillers = self.drain(b)
        times, stats = self.insert_session(b, table, nbytes, f"{item}-insert")
        self.emit(b, rnd, item, it, "drain_fillers", fillers)
        for tag, sec, st in zip(("after_delete", "no_delete"), times, stats):
            self.emit(b, rnd, item, it, f"{tag}_ms", round(sec * 1000, 3))
            for k, v in st.items():
                self.emit(b, rnd, item, it, f"{tag}_{k}", v)

    def concurrent(self, b, rnd, it, workers):
        """Item 5: one delete arms the file, then `workers` sessions released together by a row lock each
        INSERT a value that needs a new page."""
        b.csql("CREATE TABLE IF NOT EXISTS bar (id INT PRIMARY KEY, x INT);\n"
               "INSERT INTO bar SELECT 1, 0 FROM db_root WHERE NOT EXISTS (SELECT 1 FROM bar);\n", "bar")
        b.csql(f"DELETE FROM t WHERE id = {b.take('t_del')};\n"
               f"UPDATE p SET v = {value_expr(str(self.key(b)), CFG['t_bytes'])} WHERE id = 1;\nCOMMIT;\n",
               "conc-delete", autocommit=False)
        fillers = self.drain(b)
        holder_sql = b._log("conc-holder.sql")
        holder_sql.write_text("UPDATE bar SET x = x + 1 WHERE id = 1;\nSELECT SLEEP(3);\nCOMMIT;\n")
        procs = []
        with open(b._log("conc-holder.out"), "wb") as hout:
            holder = subprocess.Popen(["csql", "-C", "--no-auto-commit", "-u", "dba", "-i", str(holder_sql), b.db],
                                      stdin=subprocess.DEVNULL, stdout=hout, stderr=subprocess.STDOUT,
                                      env=b.env, cwd=b.root)
            time.sleep(0.7)
            for w in range(workers):
                k = self.key(b)
                sql_path = b._log(f"conc-w{w}.sql")
                sql_path.write_text(
                    "SET @collect_exec_stats = 1;\nSELECT id FROM t WHERE id = 1;\n"
                    "UPDATE bar SET x = x + 1 WHERE id = 1;\n"
                    f"INSERT INTO t SELECT {k}, {value_expr(str(k), 10000)} FROM db_root;\nSHOW EXEC STATISTICS;\n")
                out_path = b._log(f"conc-w{w}.out")
                fh = open(out_path, "wb")
                procs.append((subprocess.Popen(["csql", "-C", "-u", "dba", "-i", str(sql_path), b.db],
                                               stdin=subprocess.DEVNULL, stdout=fh, stderr=subprocess.STDOUT,
                                               env=b.env, cwd=b.root), fh, out_path))
            holder.wait(timeout=120)
        self.emit(b, rnd, "concurrent", it, "drain_fillers", fillers)
        for w, (pr, fh, out_path) in enumerate(procs):
            pr.wait(timeout=300)
            fh.close()
            times, stats = parse_session(out_path.read_text(errors="replace"))
            if len(times) != 2 or len(stats) != 1:
                raise RuntimeError(f"{b.label}: concurrent worker {w} parse failed, see {out_path}")
            self.emit(b, rnd, "concurrent", it, f"w{w}_ms", round(times[1] * 1000, 3))
            self.emit(b, rnd, "concurrent", it, f"w{w}_data_page_fetches", stats[0]["data_page_fetches"])

    def round(self, b, rnd, iters):
        b.start()
        try:
            # item 1: first growth after a restart (boot rule / unknown mark)
            times, stats = self.insert_session(b, "t", 10000, "restart-insert")
            for tag, sec, st in zip(("first", "second"), times, stats):
                self.emit(b, rnd, "restart", 0, f"{tag}_ms", round(sec * 1000, 3))
                for k, v in st.items():
                    self.emit(b, rnd, "restart", 0, f"{tag}_{k}", v)
            if self.plain_n:
                # no delete since the restart lap: every INSERT needs a new page and the gate is idle
                times, stats = self.insert_session(b, "t", 10000, "plain-insert", n=self.plain_n)
                for i, (sec, st) in enumerate(zip(times, stats)):
                    self.emit(b, rnd, "plain", i, "ms", round(sec * 1000, 3))
                    self.emit(b, rnd, "plain", i, "data_page_fetches", st["data_page_fetches"])
            self.insert_session(b, "u", 10000, "warm-u", n=1)
            self.drain(b)
            for it in range(iters):
                # item 2: delete one row whose page then becomes empty
                self.delete_then_insert(b, rnd, "delete_empties", it, "t", b.take("t_del"), 10000)
            for it in range(iters):
                # item 3: delete one of two chunks on a page (odd ids only); the page stays in use
                self.delete_then_insert(b, rnd, "delete_keeps", it, "u", 2 * b.take("u_del") - 1, 10000)
            for it in range(self.conc_iters):
                self.concurrent(b, rnd, it, self.workers)
        finally:
            b.stop()

    def churn(self, b, rep, cycles):
        b.start()
        try:
            rows, nbytes = CFG["c_rows"], CFG["c_bytes"]
            b.csql("DROP TABLE IF EXISTS c;\nCREATE TABLE c (id INT PRIMARY KEY, v BIT VARYING);\n"
                   f"INSERT INTO c SELECT id, {value_expr('id', nbytes)} FROM nums WHERE id <= {rows};\n", "churn-init")
            self.emit(b, rep, "churn", 0, "pages_initial", b.oos("c")["Oos_num_user_pages"])

            def drain_c(target):
                for i in range(600):
                    if b.oos("c").get("Oos_num_recs") == target:
                        return i
                    b.run(["csql", "-C", "-u", "dba", "-c",
                           "INSERT INTO f SELECT id, REPEAT('f', 1500) FROM nums WHERE id <= 200", b.db], "filler")
                    time.sleep(0.1)
                raise RuntimeError(f"{b.label}: churn drain stuck")

            for cy in range(1, cycles + 1):
                salt = 100000 * cy
                b.csql(f"UPDATE c SET v = {value_expr(f'id + {salt}', nbytes)};\n", f"churn-update-{cy}")
                self.emit(b, rep, "churn", cy, "pages_peak_update", b.oos("c")["Oos_num_user_pages"])
                drain_c(rows)
                self.emit(b, rep, "churn", cy, "pages_after_update_drain", b.oos("c")["Oos_num_user_pages"])
                b.csql("DELETE FROM c WHERE MOD(id, 10) < 3;\n", f"churn-delete-{cy}")
                drain_c(rows - rows * 3 // 10)
                self.emit(b, rep, "churn", cy, "pages_after_delete_drain", b.oos("c")["Oos_num_user_pages"])
                b.csql(f"INSERT INTO c SELECT id, {value_expr(f'id + {salt} + 7', nbytes)} FROM nums "
                       f"WHERE id <= {rows} AND MOD(id, 10) < 3;\n", f"churn-reinsert-{cy}")
                self.emit(b, rep, "churn", cy, "pages_after_reinsert", b.oos("c")["Oos_num_user_pages"])
        finally:
            b.stop()
        for table, n in b.oos_sectors().items():
            self.emit(b, rep, "churn", cycles, f"sectors_{table}", n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--build", action="append", required=True,
                    help="label=INSTALL=SHA (repeatable; rounds alternate the order)")
    ap.add_argument("--scale", type=float, default=1.0, help="multiply the row counts (smoke runs)")
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--iters", type=int, default=5)
    ap.add_argument("--churn-reps", type=int, default=0)
    ap.add_argument("--churn-cycles", type=int, default=6)
    ap.add_argument("--create", action="store_true")
    ap.add_argument("--conc-iters", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--plain", type=int, default=0, help="consecutive no-delete INSERTs per round")
    ap.add_argument("--skip-rounds", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    for k in ("t_rows", "u_rows", "c_rows"):
        CFG[k] = int(CFG[k] * a.scale)
    out.mkdir(parents=True, exist_ok=True)
    builds = []
    for i, spec in enumerate(a.build):
        label, install, sha = spec.split("=", 2)
        builds.append(Build(label, install, sha, out / label, 35100 + 10 * i))
    r = Runner(out)
    r.conc_iters, r.workers, r.plain_n = a.conc_iters, a.workers, a.plain
    if a.create:
        for b in builds:
            info = b.create()
            print(b.label, "loaded", info, flush=True)
    order = list(builds)
    for _ in range(0 if a.skip_rounds else a.rounds):
        for b in order:
            rnd = b.take("rounds") - 1
            print(f"== round {rnd} {b.label} {time.strftime('%T')} load={os.getloadavg()[0]:.1f}", flush=True)
            r.emit(b, rnd, "host", 0, "loadavg1", round(os.getloadavg()[0], 1))
            r.round(b, rnd, a.iters)
        order.reverse()
    for rep in range(a.churn_reps):
        for b in (builds if rep % 2 == 0 else builds[::-1]):
            print(f"== churn {rep} {b.label} {time.strftime('%T')}", flush=True)
            r.churn(b, rep, a.churn_cycles)
    return 0


if __name__ == "__main__":
    sys.exit(main())
