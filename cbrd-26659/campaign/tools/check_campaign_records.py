#!/usr/bin/env python3
"""Check the CBRD-26659 requirement catalogue and traceability schemas (ticket 12).

Every check encodes one acceptance criterion of ticket 12 or one rule of the campaign
specification. Expected values (family names, outcome taxonomy, the section-6 scenario
list, the accepted-but-unimplemented designs, the mixed-era statements) are copied from
the specification and the normative context, never derived from the files under test.

Usage: python3 tools/check_campaign_records.py   (from cbrd-26659/campaign/)
Exit status 0 when every check passes; 1 otherwise. No third-party modules.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from minischema import unsupported_keywords, validate  # noqa: E402

CAMPAIGN = Path(__file__).resolve().parent.parent
CATALOGUE = CAMPAIGN / "catalogue" / "requirements.json"
SCENARIO_MAP = CAMPAIGN / "catalogue" / "scenario-map.json"
SCHEMAS = CAMPAIGN / "schemas"

# --- fixed vocabulary from the campaign specification and ticket 11 --------------------
FAMILIES = [
    "Representation",
    "SQL operations",
    "Read paths",
    "Schema and utilities",
    "Concurrent lifetime",
    "Durability",
    "Operational features",
    "Resource pressure",
]
FAMILY_CODES = {
    "Representation": "REP",
    "SQL operations": "SQL",
    "Read paths": "RD",
    "Schema and utilities": "SCH",
    "Concurrent lifetime": "CL",
    "Durability": "DUR",
    "Operational features": "OPS",
    "Resource pressure": "RES",
}
REQUIREMENT_STATUSES = ["assertable", "observation-only", "BLOCKED", "UNSUPPORTED"]
CITATION_KINDS = ["context-heading", "adr", "accepted-design"]
OUTCOMES = ["PASS", "FAIL", "SKIP", "UNSUPPORTED", "BLOCKED"]

# Ticket 11: normative context pin and accepted ADR hashes (SHA256SUMS in ticket11-evidence).
CONTEXT_REVISION = "f6543de680b91ae357466b72a983f982892859cd"
DOCUMENT_HASHES = {
    "OOS-CONTEXT.md": "sha256:c9daf3c4ed25e16356ebf3c79c55f6bb7391d76c5664675a9aaf55cd5ac11698",
    "ADR-0001": "sha256:9531a213d24c44353902264de5840dd65c170246a64ff968adec797d29598e55",
    "ADR-0002": "sha256:2bdcbce486a97f29acbd4a75d5f45858d0f09205b886480238db22930810e528",
    "ADR-0003": "sha256:09a8649904e63094fa39f984e5290ccbd9dc68bc930bef916b780b4274605585",
    "ADR-0004": "sha256:2a4b94c06782e17db1cfeab3a5d953617730873dcabb6d8ad928e23e7e50c155",
}
ENGINE_BASELINE = "f4299ac0cd777a2a964c1f197ae5ebf9841a4936"

# Ticket 12: accepted-but-unimplemented designs that must appear as BLOCKED or UNSUPPORTED.
ACCEPTED_UNIMPLEMENTED = {
    "CBRD-27230": "UPDATE chain reuse",
    "CBRD-26939": "durable CDC supplemental images (ADR-0004)",
    "CBRD-27057": "four-record target (absent at the pin per ticket 11)",
    "CBRD-26950": "24-byte identity layout (absent at the pin per ticket 11)",
}
# Ticket 12: mixed-era statements from the invariants research, each a Specification gap.
MIXED_ERA_TOPICS = [
    "cross-version-sharing-wording",
    "deferred-reuse-text",
    "stub-size-terminology",
    "unconditional-reclamation",
]

# OOS-CONTEXT.md section 6 "Test Scenarios" at the pinned hash: 36 scenarios.
SECTION6_SCENARIOS = [
    "1.1", "1.2", "1.3", "1.4",
    "2.1", "2.2", "2.3",
    "3.1", "3.2",
    "4.1", "4.2", "4.3", "4.4",
    "5.1", "5.2", "5.3", "5.4", "5.5",
    "6.1", "6.2", "6.3",
    "7.1", "7.2", "7.3",
    "8.1", "8.2", "8.3", "8.4",
    "9.1", "9.2", "9.3", "9.4", "9.5", "9.6",
    "10.1", "10.2",
]

# Spec "Outcomes, replay and minimization": every replay bundle item, "missing" recordable.
REPLAY_BUNDLE_ITEMS = [
    "workload",
    "seed_and_generator_version",
    "session_and_barrier_trace",
    "injection_acknowledgements",
    "engine_identity",
    "testcase_identity",
    "specification_identity",
    "build_and_configuration_identity",
    "instrumentation_identity",
    "fixture_identity",
    "expected_versus_actual",
    "logs",
    "cores",
    "replay_command_with_prerequisites",
]

failures = []


def fail(check, message):
    failures.append(f"[{check}] {message}")


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def check_schema_subset():
    """Every campaign schema must stay inside the subset minischema evaluates."""
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        for where, keyword in unsupported_keywords(load_json(path)):
            fail("schema-subset", f"{path.name}: {where} uses {keyword!r}, which minischema ignores")


def schema_validate(check, instance, schema, label):
    for error in validate(instance, schema):
        fail(check, f"{label}: {error}")


# --- requirement catalogue --------------------------------------------------------------
def check_catalogue():
    if not CATALOGUE.exists():
        fail("catalogue-exists", f"{CATALOGUE} is missing")
        return None
    schema_path = SCHEMAS / "requirement.schema.json"
    if not schema_path.exists():
        fail("catalogue-schema-exists", f"{schema_path} is missing")
        return None
    catalogue = load_json(CATALOGUE)
    schema = load_json(schema_path)
    schema_validate("catalogue-schema", catalogue, schema, "requirements.json")

    pin = catalogue.get("pin", {})
    if pin.get("engine_baseline") != ENGINE_BASELINE:
        fail("pin-engine", f"engine_baseline {pin.get('engine_baseline')!r} != ticket 11 pin")
    if pin.get("context_revision") != CONTEXT_REVISION:
        fail("pin-context", f"context_revision {pin.get('context_revision')!r} != ticket 11 pin")
    for doc, digest in DOCUMENT_HASHES.items():
        if pin.get("content_hashes", {}).get(doc) != digest:
            fail("pin-hash", f"content hash for {doc} does not match ticket 11")

    requirements = catalogue.get("requirements", [])
    ids = [r.get("id") for r in requirements]
    for dup in {i for i in ids if ids.count(i) > 1}:
        fail("id-unique", f"requirement id {dup!r} appears more than once")

    by_id = {r["id"]: r for r in requirements if "id" in r}
    families_seen = set()
    for req in requirements:
        rid = req.get("id", "<no id>")
        fam = req.get("family")
        families_seen.add(fam)
        if fam in FAMILY_CODES and not rid.startswith(f"OOS-{FAMILY_CODES[fam]}-"):
            fail("id-family-code", f"{rid}: id prefix does not match family {fam!r}")

        # exactly one citation carrying the pinned revision and content hash
        cit = req.get("citation")
        if isinstance(cit, list):
            fail("one-citation", f"{rid}: citation must be one object, not a list")
            continue
        if not isinstance(cit, dict):
            fail("one-citation", f"{rid}: citation missing")
            continue
        doc = cit.get("document")
        if cit.get("revision") != CONTEXT_REVISION:
            fail("citation-revision", f"{rid}: citation revision is not the ticket 11 pin")
        if DOCUMENT_HASHES.get(doc) != cit.get("content_hash"):
            fail("citation-hash", f"{rid}: content hash does not match {doc!r} at the pin")
        kind = cit.get("kind")
        if kind == "adr" and not str(doc).startswith("ADR-"):
            fail("citation-kind", f"{rid}: adr citation must cite an ADR document")
        if kind in ("context-heading", "accepted-design") and doc != "OOS-CONTEXT.md":
            fail("citation-kind", f"{rid}: {kind} citation must cite OOS-CONTEXT.md")
        if kind == "accepted-design" and not re.search(r"CBRD-\d+", cit.get("source", "")):
            fail("citation-kind", f"{rid}: accepted-design citation must name its CBRD design")

        # status, gap kind and authority policy agree (ticket 10 policy, ticket 12 criterion)
        status = req.get("status")
        gap = req.get("gap_kind")
        policy = req.get("authority", {}).get("policy")
        expected_gap = {"BLOCKED": "Specification gap", "UNSUPPORTED": "Capability gap"}.get(status)
        if expected_gap and gap != expected_gap:
            fail("status-gap", f"{rid}: status {status} requires gap_kind {expected_gap!r}, got {gap!r}")
        if status in ("assertable", "observation-only") and gap is not None:
            fail("status-gap", f"{rid}: status {status} must have gap_kind null, got {gap!r}")
        allowed_policies = {
            "assertable": {"assert", "assert-after-eligibility"},
            "observation-only": {"observe"},
            "BLOCKED": {"withhold"},
            "UNSUPPORTED": {"withhold"},
        }.get(status, set())
        if policy not in allowed_policies:
            fail("status-policy", f"{rid}: status {status} allows policies {sorted(allowed_policies)}, got {policy!r}")
        if status == "BLOCKED" and not req.get("authority_question"):
            fail("blocked-question", f"{rid}: BLOCKED requirement must state its authority question")
        if status == "UNSUPPORTED" and not req.get("accepted_design"):
            fail("unsupported-design", f"{rid}: UNSUPPORTED requirement must name the accepted design")
        for other in req.get("related", []):
            if other not in by_id:
                fail("related-exists", f"{rid}: related id {other!r} is not in the catalogue")

    for fam in FAMILIES:
        if fam not in families_seen:
            fail("eight-families", f"family {fam!r} has no requirement")

    # accepted-but-unimplemented designs are present and never counted as assertable
    for ticket, label in ACCEPTED_UNIMPLEMENTED.items():
        hits = [r for r in requirements if (r.get("accepted_design") or "").startswith(ticket)]
        if not hits:
            fail("accepted-unimplemented", f"{ticket} ({label}) has no requirement")
        for r in hits:
            if r.get("status") not in ("BLOCKED", "UNSUPPORTED"):
                fail("accepted-unimplemented",
                     f"{r['id']}: {ticket} must be BLOCKED or UNSUPPORTED, got {r.get('status')}")

    # mixed-era specification statements are Specification-gap requirements
    for topic in MIXED_ERA_TOPICS:
        hits = [r for r in requirements if r.get("specification_gap_topic") == topic]
        if not hits:
            fail("mixed-era", f"no Specification-gap requirement for topic {topic!r}")
        for r in hits:
            if r.get("status") != "BLOCKED" or not r.get("authority_question"):
                fail("mixed-era", f"{r['id']}: topic {topic!r} must be BLOCKED with an authority question")

    # authority policy encodes reclamation preconditions
    if not any(r.get("authority", {}).get("policy") == "assert-after-eligibility" for r in requirements):
        fail("reclamation-policy", "no requirement uses the assert-after-eligibility policy")
    return catalogue


# --- section 6 scenario map -------------------------------------------------------------
def check_scenario_map(catalogue):
    if not SCENARIO_MAP.exists():
        fail("scenario-map-exists", f"{SCENARIO_MAP} is missing")
        return
    schema_path = SCHEMAS / "scenario-map.schema.json"
    if not schema_path.exists():
        fail("scenario-map-schema-exists", f"{schema_path} is missing")
        return
    scenario_map = load_json(SCENARIO_MAP)
    schema_validate("scenario-map-schema", scenario_map, load_json(schema_path), "scenario-map.json")
    known_ids = {r["id"] for r in (catalogue or {}).get("requirements", []) if "id" in r}
    entries = scenario_map.get("scenarios", [])
    listed = [e.get("scenario") for e in entries]
    for missing in SECTION6_SCENARIOS:
        if missing not in listed:
            fail("scenario-coverage", f"section 6 scenario {missing} is not mapped")
    for extra in set(listed) - set(SECTION6_SCENARIOS):
        fail("scenario-coverage", f"scenario {extra!r} is not in section 6 at the pinned hash")
    for dup in {s for s in listed if listed.count(s) > 1}:
        fail("scenario-coverage", f"scenario {dup} mapped more than once")
    for entry in entries:
        sid = entry.get("scenario")
        reqs = entry.get("requirements", [])
        exclusion = entry.get("exclusion")
        if not reqs and not exclusion:
            fail("scenario-mapped-or-excluded", f"scenario {sid} has neither a requirement nor an exclusion")
        if exclusion and not exclusion.get("reason"):
            fail("scenario-mapped-or-excluded", f"scenario {sid} exclusion lacks a reason")
        for rid in reqs:
            if rid not in known_ids:
                fail("scenario-requirement-exists", f"scenario {sid} cites unknown requirement {rid!r}")


# --- record schemas: manifest, matrix, attempt record, replay bundle ----------------------
RECORD_SCHEMAS = ["manifest", "matrix", "attempt-record", "replay-bundle"]


def check_record_schemas():
    schemas = {}
    for name in RECORD_SCHEMAS:
        path = SCHEMAS / f"{name}.schema.json"
        if not path.exists():
            fail("record-schema-exists", f"{path} is missing")
            continue
        schemas[name] = load_json(path)

    # the fixed outcome taxonomy is identical in every record schema that carries one
    for name in ("manifest", "matrix", "attempt-record"):
        schema = schemas.get(name)
        if not schema:
            continue
        outcome = schema.get("$defs", {}).get("outcome", {}).get("enum")
        if outcome != OUTCOMES:
            fail("outcome-taxonomy", f"{name}: $defs.outcome.enum {outcome!r} != {OUTCOMES!r}")
        evidence = schema.get("$defs", {}).get("evidence_status", {}).get("enum")
        if evidence != ["proven", "reused", "missing", "not-applicable"]:
            fail("evidence-status", f"{name}: $defs.evidence_status.enum is {evidence!r}")

    # the replay bundle lists every spec item and can record each as missing
    bundle = schemas.get("replay-bundle")
    if bundle:
        items = bundle.get("properties", {}).get("items", {})
        required = sorted(items.get("required", []))
        if required != sorted(REPLAY_BUNDLE_ITEMS):
            fail("replay-items", f"replay-bundle items.required {required} != spec list")
        states = bundle.get("$defs", {}).get("item_state", {}).get("enum", [])
        for state in ("present", "missing", "not-applicable"):
            if state not in states:
                fail("replay-item-state", f"replay-bundle item_state lacks {state!r}")

    # the matrix keeps flakiness, known-issue and attribution as separate row fields and
    # accepted exclusions are dated, user-only entries
    matrix = schemas.get("matrix")
    if matrix:
        row_required = matrix.get("$defs", {}).get("row", {}).get("required", [])
        for field in ("requirement", "case", "configuration", "run", "oos_evidence", "finding",
                      "flakiness", "known_issue", "attribution"):
            if field not in row_required:
                fail("matrix-row-fields", f"matrix row does not require {field!r}")
        excl = matrix.get("$defs", {}).get("accepted_exclusion", {})
        for field in ("requirement", "date", "reason", "accepted_by"):
            if field not in excl.get("required", []):
                fail("matrix-exclusion-fields", f"accepted_exclusion does not require {field!r}")
        if excl.get("properties", {}).get("accepted_by", {}).get("const") != "user":
            fail("matrix-exclusion-user-only", "accepted_exclusion.accepted_by must be const 'user'")

    # the manifest carries the invocation identity the spec demands
    manifest = schemas.get("manifest")
    if manifest:
        inv = manifest.get("properties", {}).get("invocation", {})
        for field in ("engine", "testcase", "context", "page_size", "build_mode", "services",
                      "instrumentation", "seed", "runner", "tier"):
            if field not in inv.get("required", []):
                fail("manifest-identity", f"manifest invocation does not require {field!r}")
        for field in ("expected", "discovered", "executed", "proof", "cases", "outstanding_coverage"):
            if field not in manifest.get("required", []):
                fail("manifest-fields", f"manifest does not require {field!r}")
        case_required = manifest.get("$defs", {}).get("case_result", {}).get("required", [])
        for field in ("case", "outcome", "oos_evidence", "attempts", "outstanding"):
            if field not in case_required:
                fail("manifest-case-fields", f"manifest case_result does not require {field!r}")

    # valid examples validate; invalid examples (negative controls) are rejected
    valid_dir = SCHEMAS / "examples" / "valid"
    invalid_dir = SCHEMAS / "examples" / "invalid"
    for name, schema in schemas.items():
        example = valid_dir / f"{name}.example.json"
        if not example.exists():
            fail("example-exists", f"{example} is missing")
        else:
            schema_validate("example-valid", load_json(example), schema, example.name)
    controls = sorted(invalid_dir.glob("*.json")) if invalid_dir.exists() else []
    seen_schema_controls = set()
    for control in controls:
        name = control.name.split("__", 1)[0]
        if name not in schemas:
            fail("negative-control", f"{control.name}: prefix {name!r} names no record schema")
            continue
        seen_schema_controls.add(name)
        if not validate(load_json(control), schemas[name]):
            fail("negative-control", f"{control.name} was accepted; the checker did not detect the planted defect")
    for name in schemas:
        if name not in seen_schema_controls:
            fail("negative-control", f"no negative control for {name}")


# --- rendered documents are fresh ---------------------------------------------------------
def check_documents():
    import render_docs
    for doc in (render_docs.CATALOGUE_DOC, render_docs.SCHEMAS_DOC):
        if not doc.exists():
            fail("document-exists", f"{doc} is missing")
    try:
        stale = render_docs.render(check_only=True)
    except (SystemExit, FileNotFoundError) as exc:
        fail("document-render", f"rendering failed: {exc}")
        return
    for name in stale:
        fail("document-fresh", f"{name} has stale generated blocks; run tools/render_docs.py")


def main():
    check_schema_subset()
    catalogue = check_catalogue()
    check_scenario_map(catalogue)
    check_record_schemas()
    check_documents()
    if failures:
        print(f"FAIL: {len(failures)} problem(s)")
        for line in failures:
            print("  " + line)
        return 1
    print("OK: all campaign record checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
