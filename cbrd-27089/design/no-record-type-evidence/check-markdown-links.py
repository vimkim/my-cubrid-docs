#!/usr/bin/env python3
"""Check local inline Markdown link targets in the supplied files (no network)."""
import json
import pathlib
import re
import sys

missing = []
for filename in sys.argv[1:]:
    source = pathlib.Path(filename)
    for line_number, line in enumerate(source.read_text().splitlines(), 1):
        for label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line):
            if target.startswith(("http:", "https:", "mailto:", "#")):
                continue
            path = re.sub(r":\d+$", "", target.split("#")[0].strip("<>"))
            resolved = pathlib.Path(path) if path.startswith("/") else source.parent / path
            if not resolved.exists():
                missing.append({"file": str(source), "line": line_number, "target": target})
print(json.dumps({"checked_files": len(sys.argv) - 1, "missing": missing}, indent=2))
sys.exit(bool(missing))
