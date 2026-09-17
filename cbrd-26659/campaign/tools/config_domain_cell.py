#!/usr/bin/env python3
"""Turn one config_domain_probe.sh observation into a cell record (campaign ticket 17).

Reads the probe's observations from T17_* environment variables and writes the JSON that
config_domain.py reads. It exists so that the probe's shell never builds JSON by hand: a
quoting accident there would silently produce a cell whose fields say something the engine
never said. Standard library only.
"""
from __future__ import annotations

import json
import os


def num(name):
    v = os.environ.get(name, "null")
    if v in ("", "null"):
        return None
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return None


def text(name):
    v = os.environ.get(name, "")
    return None if v in ("", "null") else v


cell = {
    "cell": os.environ["T17_CELL"],
    "page_size": num("T17_PAGE"),
    "build": os.environ["T17_BUILD"],
    "run_mode": os.environ["T17_MODE"],
    "verdict": os.environ["T17_VERDICT"],
    "engine_commit": os.environ["T17_COMMIT"],
    "cubrid_rel": text("T17_REL"),
    "install": text("T17_INSTALL"),
    "database": text("T17_DB"),
    "binaries": {
        "libcubrid.so": text("T17_LIB"),
        "libcubridsa.so": text("T17_LIBSA"),
        "csql": text("T17_CSQL"),
        "cub_server": text("T17_SERVER"),
    },
    "page_size_readback": num("T17_READBACK"),
    "oos_evidence": {
        "has_oos_file": num("T17_HASOOS"),
        "oos_num_recs": num("T17_NUMRECS"),
        "oos_recs_sumlen": num("T17_SUMLEN"),
    },
    "value_roundtrip": text("T17_ROUNDTRIP"),
    "wall_seconds": num("T17_WALL"),
    "reason": text("T17_REASON"),
    "install_conf_restored": text("T17_CONF"),
    "evidence_dir": text("T17_WORK"),
}
if cell["verdict"] != "runnable":
    cell["oos_evidence"] = None
print(json.dumps(cell, indent=2, sort_keys=True))
