#!/usr/bin/env python3
"""Extract CTest-prefixed case receipts without counting CTest failure echoes."""
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent
receipts = {}
for name in ("focused-baseline", "focused-before-json-strengthening", "focused-final", "oos-full-before-formatting", "oos-full-ba308c529", "focused-repair-final", "oos-full-final"):
    path = root / f"{name}.log"
    if not path.exists():
        continue
    log = path.read_text()
    cases = {}
    for match in re.finditer(r"^(\d+): \[ RUN      \] (\S+)$", log, re.M):
        cases[(match[1], match[2])] = {"ctest_number": int(match[1]), "case": match[2], "outcome": "INCOMPLETE"}
    for match in re.finditer(r"^(\d+): \[\s+(OK|FAILED|SKIPPED)\s+\] (\S+) \((\d+) ms\)$", log, re.M):
        key = (match[1], match[3])
        if key in cases:
            cases[key]["outcome"] = {"OK": "PASS", "FAILED": "FAIL", "SKIPPED": "SKIP"}[match[2]]
            cases[key]["duration_ms"] = int(match[4])
    receipts[name] = {
        "log": path.name,
        "summary": re.findall(r"^\d+% tests passed, \d+ tests failed out of \d+$", log, re.M),
        "executed": len(cases),
        "cases": list(cases.values()),
    }

baseline = receipts["focused-baseline"]
for name in ("focused-final", "oos-full-ba308c529", "focused-repair-final", "oos-full-final"):
    if name not in receipts:
        continue
    for number, expected in ((36, 21), (24, 13)):
        base_cases = {c["case"] for c in baseline["cases"] if c["ctest_number"] == number}
        new_cases = [c for c in receipts[name]["cases"] if c["ctest_number"] == number]
        if len(new_cases) != expected or any(c["outcome"] == "INCOMPLETE" for c in new_cases):
            continue  # The full suite may still be running while gathering progress.
        assert {c["case"] for c in new_cases} == base_cases, (name, number)
        assert all(c["outcome"] == "PASS" for c in new_cases), (name, number)
        receipts[name].setdefault("requested_case_identity_checks", {})[str(number)] = {
            "expected": expected, "executed": len(new_cases), "passed": expected, "same_cases_as_baseline": True
        }

xml_receipts = {}
for path in sorted((root / "gtest-full").glob("*.xml")):
    xml = ET.parse(path).getroot()
    xml_receipts[path.name] = {
        "tests": int(xml.attrib["tests"]),
        "failures": int(xml.attrib["failures"]),
        "disabled": int(xml.attrib["disabled"]),
        "cases": [dict(case.attrib) for case in xml.findall(".//testcase")],
    }
receipts["gtest_xml"] = xml_receipts
(root / "case-receipts.json").write_text(json.dumps(receipts, indent=2) + "\n")
for name, receipt in receipts.items():
    if name == "gtest_xml":
        print(f"GTest XML: {len(receipt)} binary receipts")
    else:
        counts = {state: sum(c["outcome"] == state for c in receipt["cases"]) for state in ("PASS", "FAIL", "SKIP", "INCOMPLETE")}
        print(f"{name}: {receipt['executed']} executed, {counts}")
