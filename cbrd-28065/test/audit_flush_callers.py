#!/usr/bin/env python3
"""For each logpb_flush_pages call in a CUBRID tree, print the function, the argument, and where that LSA came from.

    python3 audit_flush_callers.py SRC_ROOT

The origin is the nearest earlier assignment to the argument inside the same function, or the caller's parameter.
"""
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
call = re.compile(r"logpb_flush_pages \(thread_p, &?(\w+)\);")
func = re.compile(r"^(\w+) \(THREAD_ENTRY \* thread_p")
for f in sorted((root / "src").rglob("*.c")):
    lines = f.read_text(errors="replace").splitlines()
    cur, start = None, 0
    for i, line in enumerate(lines):
        m = func.match(line)
        if m:
            cur, start = m.group(1), i
        m = call.search(line)
        if not m or line.lstrip().startswith("*"):
            continue
        var = m.group(1)
        origin = "parameter of " + cur
        for j in range(i - 1, start, -1):
            if re.search(rf"\b{var}\s*=\s*\w", lines[j]) or re.search(rf"\(thread_p, \w+, &{var}\b|&{var}\)", lines[j]):
                origin = f"{lines[j].strip()}  (line {j + 1})"
                break
        print(f"{f.relative_to(root)}:{i + 1}  {cur}  arg={var}  <- {origin}")
