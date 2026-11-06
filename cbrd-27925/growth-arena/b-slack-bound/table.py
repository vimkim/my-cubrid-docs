#!/usr/bin/env python3
"""Print the REPORT.md result table from the per-job JSON files of run.py.

One row per (design, setting). Two MaxPages per cell must agree on the worst size, else the
cell says so. Usage: python3 -I -B table.py RUN_DIR [RUN_DIR ...]
"""
import glob
import json
import os
import sys

ORDER = ["cand_fullboot", "slack_set_K1", "slack_set_K2", "slack_set_K1_noboot", "count_K0",
         "slack_count_K1", "slack_count_K1_noboot", "cand_freegate"]
SETTING = {(False, False): "조용", (False, True): "쓰기", (True, False): "크래시+조용", (True, True): "크래시+쓰기"}


def main():
    rows = {}
    for d in sys.argv[1:]:
        for f in glob.glob(os.path.join(d, "*.json")):
            if f.endswith("results.json"):
                continue
            with open(f) as fh:
                r = json.load(fh)
            rows.setdefault((r["design"], r["crashes"], r["writes"]), []).append(r)
    print("| 설계 | 설정 | 현재 명세 | slack 명세 | 최악 크기 R | 성장당 최대 검사 | 헛된 검사 | 최대 drift "
          "| MaxPages | 상태 수 | TLC 시간(s) |")
    print("|" + " --- |" * 11)
    for (design, c, w), rs in sorted(rows.items(), key=lambda kv: (ORDER.index(kv[0][0]), kv[0][1], kv[0][2])):
        rs.sort(key=lambda r: r["max_pages"])
        big = rs[-1]
        sizes = {("cap" if r["overflow"] else r["R"]) for r in rs}
        size = sizes.pop() if len(sizes) == 1 else "/".join(str(r["R"]) for r in rs) + " (cap마다 다름)"
        pf = lambda flag: "FAIL" if any(r[flag] for r in rs) else "PASS"
        print(f"| {design} | {SETTING[(c, w)]} | {pf('strongBroken')} | {pf('weakBroken')} | {size} "
              f"| {max(r['examined'] for r in rs)} | {'있음' if any(r['futile'] for r in rs) else '없음'} "
              f"| {max(r['maxDrift'] for r in rs)} | {','.join(str(r['max_pages']) for r in rs)} "
              f"| {big['states']:,} | {big['secs']} |")


if __name__ == "__main__":
    main()
