#!/usr/bin/env python3
"""Validate the ticket 14 campaign records against ticket 12's schemas.

Not a duplicate of campaign/tools/check_campaign_records.py, which validates the
requirement catalogue, the schemas themselves and the schemas' own valid and invalid
examples -- it never looks at a ticket's records. This validates *this ticket's* manifests,
attempt records, replay-bundle indexes and matrix against those schemas, using the same
minischema evaluator, so the records are judged by exactly the code that judges the
examples. Both are run; both must pass.
"""
import json
import sys
from pathlib import Path

CAMPAIGN = Path("/home/vimkim/gh/my-cubrid-docs/cbrd-26659/campaign")
sys.path.insert(0, str(CAMPAIGN / "tools"))
from minischema import validate  # noqa: E402

EVIDENCE = CAMPAIGN / "evidence" / "ticket14"
PAIRS = [
    ("manifest.schema.json", sorted(EVIDENCE.glob("inv-*.json"))),
    ("attempt-record.schema.json", sorted(EVIDENCE.glob("att-T14-*.json"))),
    ("replay-bundle.schema.json", sorted(EVIDENCE.glob("bundle-*.json"))),
    ("matrix.schema.json", sorted(EVIDENCE.glob("matrix.json"))),
]

failures = 0
for schema_name, files in PAIRS:
    schema = json.loads((CAMPAIGN / "schemas" / schema_name).read_text())
    for f in files:
        errors = list(validate(json.loads(f.read_text()), schema))
        if errors:
            failures += 1
            print(f"[FAIL] {f.name} against {schema_name}")
            for e in errors:
                print(f"       {e}")
        else:
            print(f"[ OK ] {f.name} against {schema_name}")
if not any(files for _, files in PAIRS):
    print("no records found")
    sys.exit(1)
sys.exit(1 if failures else 0)
