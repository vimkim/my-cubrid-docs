#!/usr/bin/env python3
"""Create churn-only databases (tables nums and f) for churn_scale.py: create_churn_dbs.py DIR label=INSTALL ..."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import churn_diag as d  # noqa: E402  (also drops CUBRID_* from the environment)

root = pathlib.Path(sys.argv[1])
for i, spec in enumerate(sys.argv[2:]):
    label, install = spec.split("=", 1)
    b = d.DiagBuild(label, install, "-", root / label, 35100 + 10 * i)
    if not (b.root / "databases.txt").exists():
        b.create_small()
        print("created", label, flush=True)
