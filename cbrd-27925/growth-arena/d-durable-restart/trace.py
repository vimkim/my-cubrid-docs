#!/usr/bin/env python3
"""Print a TLC counterexample from a log as one line per step: the action and the chosen variables."""
import re
import sys

KEYS = ["pg", "R", "live", "busy", "pend", "gpc", "cand", "checked", "unknown", "lapLeft",
        "cursor", "logEv", "ck", "ckNew", "bootR"]
text = open(sys.argv[1]).read()
for m in re.finditer(r"^State (\d+): <(\w+)[^>]*>\n(.*?)(?=^State \d+:|\Z|^\d+ states generated)", text, re.S | re.M):
    n, act, body = m.groups()
    vals = {}
    for line in re.finditer(r"^/\\ (\w+) = (.*)$", body, re.M):
        vals[line.group(1)] = line.group(2).strip()
    print(n, act, " ".join(f"{k}={vals[k]}" for k in KEYS if k in vals))
