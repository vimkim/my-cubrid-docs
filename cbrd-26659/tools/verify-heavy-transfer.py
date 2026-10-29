#!/usr/bin/env python3
"""Verify the paired PR8128 heavy import and regular-shell exclusion."""

import argparse
import csv
import hashlib
from pathlib import Path
import stat
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--regular", required=True, type=Path)
parser.add_argument("--heavy", required=True, type=Path)
args = parser.parse_args()
regular = args.regular.resolve()
heavy = args.heavy.resolve()
source = "02d023932b8aa39b2807cc6a77d72f3d58e231d6"

with (heavy / "shell_heavy/_40_guava/oos_common/pr8128-transfer.tsv").open() as stream:
    transfer = list(csv.DictReader(stream, delimiter="\t"))
with (regular / "disabled/heavy/oos-pr8128.tsv").open() as stream:
    archive = list(csv.DictReader(stream, delimiter="\t"))
with (regular / "disabled/oos-pr8128-inventory.tsv").open() as stream:
    inventory = list(csv.DictReader(stream, delimiter="\t"))

assert len(transfer) == len({row["original_path"] for row in transfer}) == 72
entries = {row["original_path"]: row for row in transfer if row["role"] == "entry"}
support = [row for row in transfer if row["role"] == "support"]
assert len(entries) == len(archive) == 38 and len(support) == 34
assert set(entries) == {row["original_path"] for row in archive}
checks = [(heavy / row["heavy_path"], row["original_path"], row) for row in transfer]
checks.extend((regular / row["disabled_path"], row["original_path"], row) for row in archive)
checks.extend((regular / row["original_path"], row["original_path"], row) for row in support)

prior_disabled = subprocess.check_output(
    ["git", "-C", str(regular), "ls-tree", "-r", "--name-only", source, "--", "disabled/"],
    text=True,
).splitlines()
prior_disabled = [path for path in prior_disabled if path.endswith(".disabled")]
assert len(prior_disabled) == 70
checks.extend((regular / path, path, None) for path in prior_disabled)

assert len(inventory) == 133
retained = [row for row in inventory if (regular / row["original_path"]).is_file()]
assert len(retained) == 31
checks.extend((regular / row["original_path"], row["original_path"], None) for row in retained)
for target, original, record in checks:
    assert target.is_file() and not target.is_symlink(), target
    expected = subprocess.check_output(["git", "-C", str(regular), "show", f"{source}:{original}"])
    mode = subprocess.check_output(
        ["git", "-C", str(regular), "ls-tree", source, "--", original], text=True
    ).split()[0]
    assert target.read_bytes() == expected, target
    assert stat.S_IMODE(target.stat().st_mode) == (int(mode, 8) & 0o777), target
    if record is not None:
        assert record["sha256"] == hashlib.sha256(expected).hexdigest(), target
        assert record["mode"] == mode, target

for row in archive:
    assert row["ci_result"] == "PASS" and float(row["seconds"]) > 20
    assert row["evidence_run_id"] == "40643373124"
    assert row["evidence_tc_sha"] == "479035a45f06545db1974e1369e88000fb98a89a"
    assert not (regular / row["original_path"]).exists()
    assert row["heavy_path"] == "shell_heavy/" + row["original_path"].removeprefix("shell/")
    assert row["disabled_path"] == "disabled/heavy/" + row["original_path"] + ".disabled"

discovered = {
    str(path.relative_to(heavy))
    for path in (heavy / "shell_heavy/_40_guava").rglob("cases/*.sh")
    if path.name == path.parent.parent.name + ".sh"
}
assert discovered == {row["heavy_path"] for row in archive}
print("PASS: 72 imports, 38 heavy entries, 38 archives, 31 retained entries, 70 prior exclusions, unchanged bytes and modes")
